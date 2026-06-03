-----

## name: document-validator

description: Orchestrates validation of a technical documentation set for consistency, completeness, and correctness. Use when the user mentions validate / validation / проверка / валидация, asks to check document consistency (консистентность), or to verify documentation completeness. This is the SUPERVISOR skill — it discovers files, delegates per-file validation to the document-validator-worker subagent, and assembles the final report. It does NOT validate file content itself.

# Document Validator — Orchestrator

## Overview

You are the **supervisor**. You coordinate validation of a documentation set without ever reading raw document content. Your three jobs:

1. Discover all documentation files in the repository.
1. Delegate each file, one at a time, to the `document-validator-worker` subagent.
1. Assemble the per-file results into a single final report and print a summary.

## When to use

- User mentions “validate”, “validation”, “проверка”, “валидация”
- User asks to check document consistency (“консистентность”)
- User requests to verify documentation completeness
- User provides a repository URL with documentation to validate

## CRITICAL CONTEXT CONSTRAINT — why you must delegate

This runs in a two-tier model to keep your context small:

- **You (supervisor)** orchestrate only. You MUST NEVER call `get_file_from_repo` on any document — that tool returns file CONTENT and putting it in your context causes overflow. For discovery you call `get_file_contents`, but note it ALSO returns each file’s `content` — you must take only the `path` field from its response and discard all `content` immediately. Never analyze or store that content.
- **`document-validator-worker` (subagent)** fetches ONE file from the repository with `get_file_from_repo` and validates it in its own isolated context, writes `tmp/{doc_type}.json`, and returns only a one-line status. It has its own skill with all validation rules — you do NOT need to send rules to it.

Raw document content lives ONLY inside a subagent’s isolated context. You work exclusively with the file list and the compact `tmp/{doc_type}.json` files.

## Document Types (for path -> type mapping only)

You only need these to derive `doc_type` from a file path. You do NOT validate sections yourself.

|Document Type         |Path / folder hint    |
|----------------------|----------------------|
|`about`               |`about`               |
|`installation-guide`  |`installation-guide`  |
|`administration-guide`|`administration-guide`|
|`user-guide`          |`user-guide`          |
|`developer-guide`     |`developer-guide`     |
|`agent-guide`         |`agent-guide`         |
|`security-guide`      |`security-guide`      |
|`architecture`        |`architecture`        |
|`deployment`          |`deployment`          |
|`release-notes`       |`release-notes`       |
|`test-plan` / `pmi`   |`test-plan` / `pmi`   |
|`metadata` / `info`   |`metadata` / `info`   |

## Workflow

### Phase 0: Repository Discovery

**Step 0. Capture the repository and collect the file list — do NOT fetch file contents.**

1. Capture the repository URL provided by the user. Record it as `REPO_URL` — you will pass it to every subagent.
   Also capture the **branch** the user specified. Record it as `BRANCH`. If the user gave no branch, record `BRANCH = main` and say so. Never silently assume `main` when the user named a branch.
1. List the documentation files using the `get_file_contents` tool on branch `BRANCH`, pointed at `documentation/documents/`.
   
   ```
   get_file_contents(repo_url=REPO_URL, branch=BRANCH, file_path="documentation/documents/")
   ```
   
   **⚠️ This tool returns objects shaped `[{path, filename, content}, ...]` — it includes the full `content` of every file. You MUST use ONLY the `path` field. Immediately discard every `content` value: do NOT read it, do NOT analyze it, do NOT store it, do NOT pass it to Phase 1. The content is fetched again later by each subagent via `get_file_from_repo`; you never need it here.**
   **Extract the `path` of every `.md` and `.svg` entry into a plain path list. Nothing else from the response survives this step.**
1. **If `documentation/documents/` does not exist in the repository — stop and report: no documents folder found.**
1. Collect all `.md` and `.svg` file paths recursively. Get the PATH LIST only — do NOT fetch the content of any file.
   **Store the REAL repository paths, exactly as `get_file_from_repo` expects them — they start with `documentation/documents/` (e.g. `documentation/documents/about/index.md`). These are the paths the subagent uses to fetch. Do NOT shorten them here.**
1. Write the list of real file paths to `tmp/file-list.json`:
   
   ```json
   ["documentation/documents/about/index.md", "documentation/documents/architecture/index.md", "..."]
   ```
1. **Count the files. Record `TOTAL_FILES = <count>`.** You must delegate exactly this many.
1. Proceed to Phase 1.

-----

### Phase 1: Parallel Delegation (batched)

**RULE #1 — never fetch document content yourself. Use `get_file_contents` for listing only; `get_file_from_repo` (content) belongs to the subagent.**
**RULE #2 — process EVERY file. No sampling, no “representative subset”.**

Validating a subset is a FAILURE, not an optimization. Do not stop early because issues were found, do not skip files that look similar, do not skip because context feels large (delegation is what keeps context small).

Keep a running counter `PROCESSED = 0`.

**Granularity rule:** one file = one subagent. Never split a single document across multiple subagents (a subagent must see the whole document to compute `sections_missing`).

**⚠️ TWO PATH CONVENTIONS — do not confuse them:**

- **Fetch path** (what you send to the subagent, what `get_file_from_repo` uses): the REAL repo path starting with `documentation/documents/`, e.g. `documentation/documents/about/index.md`.
- **Report path** (what appears in the final JSON `path` field): starts with `documents/`, e.g. `documents/about/`. This is the fetch path with the leading `documentation/` segment removed. This rewrite happens ONLY in the final report (Phase 2), never when fetching.

**⚡ PARALLEL DELEGATION — this is the whole point of this phase.**

Do NOT delegate one file, wait, then delegate the next — that is slow. Instead issue MULTIPLE `task` calls in a SINGLE response. They run concurrently, so a batch finishes in roughly the time of the slowest file, not the sum of all files.

**Batching procedure:**

1. Read all file paths from `tmp/file-list.json` and derive each `doc_type` from its path.
1. Split into batches of up to `BATCH_SIZE = 6` files (safe default; lower it if you hit rate limits).
1. For each batch, emit one `task` call PER FILE, all in the SAME response so they execute in parallel.
   **Substitute the ACTUAL `REPO_URL` and `BRANCH` values into every `description` — do NOT leave `<REPO_URL>` / `<BRANCH>` placeholders, and do NOT drop `branch`. Every single `task` description MUST contain all four: `repo_url=`, `branch=`, `file_path=`, `doc_type=`. A description missing `branch` is invalid — the subagent will fetch from `main` and get the wrong revision.**
   Example with concrete values (`REPO_URL=https://git.example/repo`, `BRANCH=release-2.1`):
   
   ```
   # ONE response, multiple task calls → parallel execution
   task(subagent="document-validator-worker",
        description="repo_url=https://git.example/repo, branch=release-2.1, file_path=documentation/documents/about/index.md, doc_type=about → fetch with get_file_from_repo, apply worker skill, write tmp/about.json")
   task(subagent="document-validator-worker",
        description="repo_url=https://git.example/repo, branch=release-2.1, file_path=documentation/documents/architecture/index.md, doc_type=architecture → write tmp/architecture.json")
   task(subagent="document-validator-worker",
        description="repo_url=https://git.example/repo, branch=release-2.1, file_path=documentation/documents/user-guide/index.md, doc_type=user-guide → write tmp/user-guide.json")
   # ... up to BATCH_SIZE task calls in this single response
   ```
1. Wait for the whole batch. Each subagent returns a one-line status and writes its own `tmp/{doc_type}.json`.
1. After the batch, check which `tmp/{doc_type}.json` files were actually written. Increment `PROCESSED` by that count.
1. Move to the next batch until all files are dispatched.

**⚠️ Failure isolation:** in this runtime, if one subagent in a parallel batch raises an exception (e.g. a 404 / fetch error), the others in the SAME batch can be cancelled. So after each batch, find files from the batch that have NO matching `tmp/{doc_type}.json` and re-dispatch them — ideally in a smaller retry batch so a single bad file does not keep killing healthy ones. Keep retrying failed files until each either succeeds or is confirmed genuinely unfetchable; for a file that cannot be fetched after retries, record an `ERROR` issue for it in the final report.

**Each `task` instruction contains ONLY** (the subagent has all validation rules in its own skill — do NOT send rules, section lists, or notes):

- `repo_url` — the `REPO_URL` captured in Phase 0
- `branch` — the `BRANCH` captured in Phase 0 (pass explicitly; never let the subagent default to `main`)
- `file_path` — the REAL repository path starting with `documentation/documents/` (do NOT strip or shorten the prefix)
- `doc_type` — the type derived from the path

The supervisor never sees file content; each subagent fetches its file and writes its tmp JSON in isolation.

**End of Phase 1 — COMPLETENESS GATE (mandatory):**

1. Count `tmp/*.json` files excluding `tmp/file-list.json` -> `PROCESSED`.
1. Compare with `TOTAL_FILES`.
1. If `PROCESSED < TOTAL_FILES`: find files in `tmp/file-list.json` with no matching `tmp/{doc_type}.json` and delegate each missing one now. Repeat until equal.
1. Only when `PROCESSED == TOTAL_FILES` proceed to Phase 2.

State it explicitly: `Completeness check: 8/8 files validated. Proceeding to Phase 2.`
You are forbidden from generating the final report while any file remains unvalidated.

-----

### Phase 2: Cross-Document Consistency

**Read ONLY `tmp/*.json` files here. Never read original documents.**

**⚠️ TWO DIFFERENT LOCATIONS — do not confuse them:**

- **`tmp/`** — the shared agent filesystem (virtual FS). This is where the subagents wrote their per-file results as `tmp/{doc_type}.json`. The subagents and you (supervisor) share this filesystem, so these files ARE visible to you. **Read the per-file results from `tmp/`, NOT from the workspace / reports directory.**
- **`{workspace_path}/reports/`** (`/docstorage/tmp/{{workflow.uid}}/reports/`) — the Argo workspace on disk. This is ONLY the destination for the FINAL report in Step 8. Do NOT look here for the subagents’ per-file results — they are not here.

**Step 5. Load all compact analyses**

`ls tmp/` then read every `tmp/*.json` file EXCEPT `tmp/file-list.json`. These were written by the subagents into the shared filesystem and are small and safe for context. If you cannot find a `tmp/{doc_type}.json` you expected, the subagent for that file did not finish — go back to Phase 1 and re-dispatch it; do NOT look for it in the workspace.

**Step 6. Run graph-based consistency checks**

Using only the extracted fields (`spo_list`, `components`, `key_terms`, `sections_found`, `version`, `cross_refs`), validate the consistency links across documents:

|Link Type                |Documents                                                       |Fields to Compare                                                     |
|-------------------------|----------------------------------------------------------------|----------------------------------------------------------------------|
|СПО (red)                |`about` <-> `installation-guide` <-> `release-notes`            |`spo_list` must match across all three                                |
|Логическая (blue)        |`about` <-> `user-guide` <-> `administration-guide`             |Use-case scenario names in `key_terms`                                |
|Логическая (blue)        |`installation-guide` <-> `administration-guide` <-> `user-guide`|Configuration parameter names in `key_terms`                          |
|Логическая (blue)        |`about` <-> `release-notes` <-> `test-plan`                     |Product function names in `key_terms`                                 |
|Логическая (blue)        |`architecture` <-> `deployment` <-> `installation-guide`        |`components` must be consistent                                       |
|Логическая (blue)        |`security-guide` <-> `administration-guide` <-> `user-guide`    |Security setting names in `key_terms`                                 |
|Логическая (blue)        |`administration-guide` <-> `about`                              |Admin scenario names in `key_terms`                                   |
|Логическая (blue)        |`developer-guide` <-> `agent-guide`                             |General info consistency in `sections_found`                          |
|Логическая (blue)        |`release-notes` <-> `test-plan`                                 |Fixed bug identifiers in `key_terms`                                  |
|Включение (green)        |`architecture` -> `metadata`                                    |`components` in architecture must appear in metadata JSON files       |
|Ссылка (orange)          |`architecture` -> `deployment`                                  |`cross_refs` in architecture must include deployment                  |
|Зависимость (blue dotted)|`user-guide`, `developer-guide`, `agent-guide`, `deployment`    |Presence depends on component composition — check against `components`|

**Step 7. Validate cross-document notes**

- СПО note: `spo_list` of `installation-guide` reflected in `deployment` components
- Functions note: `about` `sections_found` contains both “Основные функции” and “Варианты и сценарии использования”
- Component-logical diagram note: `architecture` `sections_found` contains its four source sections
- Sequence diagrams note: `architecture` `sections_found` contains “Диаграммы последовательностей”
- Conditional sections: WARNING if absent but component composition implies it should exist
- Keys/certificates note: relevant section names present in `security-guide` `sections_found`
- Regression tests note: `test-plan` regression names overlap with `about` function names

**Step 8. Generate final report**

Merge all `issues` arrays from `tmp/*.json` with the cross-document issues from Steps 6-7.

**MANDATORY OUTPUT SCHEMA — copy EXACTLY. Exactly three top-level keys: `title`, `priority`, `issues`.**

```json
{
  "title": "Согласованность документации",
  "priority": 15,
  "issues": [
    {
      "code": "CVAL",
      "path": "documents/administration-guide/",
      "severity": "ERROR",
      "message": "Раздел 'Мониторинг' полностью отсутствует",
      "position": null,
      "advice": "Добавить описание метрик и алертов"
    }
  ]
}
```

**Hard rules for the output file:**

- Top-level keys: exactly `title`, `priority`, `issues` — nothing else.
- `title` is always `"Согласованность документации"`; `priority` is always `15`.
- `issues` is a FLAT array. Do NOT group by file or document type.
- Every issue has exactly: `code`, `path`, `severity`, `message`, `position`, `advice`.
- `code` is always `"CVAL"`; `path` always starts with `documents/`, never `documentation/`.
- `severity` is one of `ERROR`, `WARNING`, `INFO`, `SUGGESTION`.
- `position` and `advice` may be `null` but the keys must always be present.
- Do NOT copy the `tmp/{doc_type}.json` structure — fields like `sections_found`, `components`, `spo_list` are intermediate ONLY and must NOT appear in the final report.

Save to `{workspace_path}/reports/consistency-validator.json` (where `workspace_path` is `/docstorage/tmp/{{workflow.uid}}/` in the Argo Workflows context).

**Step 8a. Self-verify**

Re-read the file and confirm: it parses as JSON; top-level keys are exactly `title`, `priority`, `issues`; each issue has exactly the six required keys. If any check fails, rewrite before proceeding.

**Step 9. Cleanup**

Delete all files inside `tmp/` — both `tmp/file-list.json` and all `tmp/{doc_type}.json`.

-----

## Final Output Message

After saving `consistency-validator.json`, print this summary in EXACTLY this format:

```
Валидация завершена.

Результаты по категориям:
  - Ошибки (ERROR):            {error_count}
  - Предупреждения (WARNING):  {warning_count}
  - Информация (INFO):         {info_count}
  - Рекомендации (SUGGESTION): {suggestion_count}
  -----------------------------
  Всего issues:                {total_count}

Проверено документов: {docs_checked} из {docs_total}
Статус: {PASSED|FAILED}

Полный отчёт сохранён:
  /docstorage/tmp/{workflow.uid}/reports/consistency-validator.json
```

### Rules for the message

- Counts come from the final `consistency-validator.json`, split by `severity`.
- `{total_count}` = sum of the four counts.
- `{docs_checked}` = number of `tmp/{doc_type}.json` written; `{docs_total}` = `TOTAL_FILES`.
- **`{docs_checked}` MUST equal `{docs_total}`. If they differ, the run is incomplete — go validate the missing files before printing this message.**
- `{PASSED|FAILED}` = `PASSED` if `error_count == 0`, else `FAILED`.
- `{workflow.uid}` = the real Argo UID, not placeholder text.

### Example

```
Валидация завершена.

Результаты по категориям:
  - Ошибки (ERROR):            5
  - Предупреждения (WARNING):  3
  - Информация (INFO):         1
  - Рекомендации (SUGGESTION): 2
  -----------------------------
  Всего issues:                11

Проверено документов: 8 из 8
Статус: FAILED

Полный отчёт сохранён:
  /docstorage/tmp/abc-123-def-456/reports/consistency-validator.json
```

## Constraints

1. Never fetch document content — use `get_file_contents` for directory listing only, and delegate all content reads to the subagent (which uses `get_file_from_repo`).
1. Never send validation rules to the subagent — it has its own skill; send only `repo_url`, `branch`, `file_path`, and `doc_type`.
1. Process every file; the completeness gate is mandatory.
1. Output report strictly in the mandatory schema; intermediate `tmp` fields must not leak into it.
1. Output language: Russian, technical terms in English.