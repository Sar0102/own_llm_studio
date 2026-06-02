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

- **You (supervisor)** orchestrate only. You MUST NEVER call `read_file` / `get_file_from_repo` on any `.md` / `.svg` document. Reading raw documents into your context causes overflow and fails the task.
- **`document-validator-worker` (subagent)** reads and validates ONE file in its own isolated context, writes `tmp/{doc_type}.json`, and returns only a one-line status. It has its own skill with all validation rules — you do NOT need to send rules to it.

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

**Step 0. Collect the file list only — do NOT read file contents.**

1. Access the repository from the provided URL.
1. Navigate to the `documentation` folder in the repository root.
1. **If `documentation` does not exist — stop and report: no documents folder found.**
1. Find all `.md` and `.svg` files recursively inside `documentation/` using directory listing / glob only (e.g. `find documentation -name '*.md'`). Do NOT open any file.
1. Write the list of file paths to `tmp/file-list.json`:
   
   ```json
   ["documents/about/index.md", "documents/architecture/index.md", "..."]
   ```
1. **Count the files. Record `TOTAL_FILES = <count>`.** You must delegate exactly this many.
1. Proceed to Phase 1.

-----

### Phase 1: Per-File Delegation Loop

**RULE #1 — never read source documents yourself.**
**RULE #2 — process EVERY file. No sampling, no “representative subset”.**

Validating a subset is a FAILURE, not an optimization. Do not stop early because issues were found, do not skip files that look similar, do not skip because context feels large (delegation is what keeps context small).

Keep a running counter `PROCESSED = 0`. Iterate `tmp/file-list.json` in order.

**For each file:**

1. Derive `doc_type` from the file path (folder name -> type, using the table above).
1. Delegate to the subagent via the `task` tool. The instruction must contain ONLY:
- `file_path` — the single file
- `doc_type` — the derived type
   
   The subagent already has all validation rules in its own skill. You do NOT send rules, section lists, or notes — only the file path and its type.
   
   ```
   task(
     subagent="document-validator-worker",
     description="Validate file_path=documents/about/index.md, doc_type=about.
                  Apply your worker skill rules and write tmp/about.json."
   )
   ```
1. Receive ONLY the one-line status, e.g. `DONE about: 3 issues, saved tmp/about.json`.
1. Increment `PROCESSED` by 1.
1. Move to the next file.

```
+--------------------------------------------------------------+
| FOR file[i] in tmp/file-list.json:                           |
|   doc_type = type from path                                  |
|   task(subagent="document-validator-worker",                 |
|        description="file_path=... , doc_type=...")            |
|   receive one-line status -> PROCESSED += 1                  |
|   go to file[i+1]                                            |
|                                                              |
| You never see file content. The subagent writes the tmp JSON.|
+--------------------------------------------------------------+
```

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

**Step 5. Load all compact analyses**

Read all `tmp/*.json` files except `tmp/file-list.json`. These are small and safe for context.

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

1. Never read raw document content — always delegate to the subagent.
1. Never send validation rules to the subagent — it has its own skill; send only `file_path` and `doc_type`.
1. Process every file; the completeness gate is mandatory.
1. Output report strictly in the mandatory schema; intermediate `tmp` fields must not leak into it.
1. Output language: Russian, technical terms in English.