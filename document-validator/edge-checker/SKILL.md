---
name: document-validator-edge-checker
description: Edge-checker for parallel documentation validation. Receives ONE edge group from graph.yaml plus the paths to the facts JSON files of that group's documents, validates every cross-document edge of the group by comparing facts, and writes the group's issues to a JSON file on disk. Invoked by the document-validator-orchestrator; never reads document content.
---

# Document Validator — Edge Checker

## OUTPUT CONTRACT (read first)

Your ONLY deliverable is a JSON file written to `output_path` on disk. The orchestrator reads it
**from disk after all edge-checkers finish** — it never reads your chat reply. Writing the file is
**mandatory and unconditional**, even when `issues` is empty. A run that ends without the file on
disk FAILED. Put the full JSON in the file; reply to the supervisor with a single line
`written: <output_path>` and nothing else.

## Overview

Validates **one group of cross-document edges** using only the compact `facts` extracted by workers.
Never reads documents, never fetches the repository. Context = a few small facts JSON files + your
group from graph.yaml — constant size regardless of documentation volume.

## Tools — local disk only

You never touch the repository. Use only local workspace tools — `read_file`, `ls`, `glob`,
`write_file` — with **absolute** paths starting with `/`: `<skill_dir>/graph.yaml`,
`<skill_dir>/error-codes.md`, the facts JSONs given in `facts_paths`, and `output_path`.

Never call repository tools (`get_single_file`, `get_multiple_files`, `get_file_list`) — they need a
git `repository_url` and will fail on a local path with `Unsupported URL format`. There is no shell
tool: never write or run scripts.

## Canonical sources

The task text gives you `skill_dir` — an **absolute** path to the skill root. Read the skill files
directly from there; all filesystem tools require absolute paths starting with `/`. **Never search
the filesystem for them** — hunting burns the execution timeout and the run is cancelled.

- **`<skill_dir>/graph.yaml`** — edge definitions: take `edge_groups.<group_id>` and every edge in `edges`
  with a matching `id` (plus `version_check` if `group_id` = GRP-VER; plus any cross-doc note whose
  `id` is listed in the group). Edge fields: `type`, `code`, `a`/`b` (doc + section + fact),
  `symmetric`, `rule`, `requires_doc`/`trigger`.
- **`<skill_dir>/error-codes.md`** — `message` templates and placeholders for each edge's code.

## Input (from orchestrator)

| Param | Description |
|---|---|
| `skill_dir` | **Absolute** path to the skill root (read `<skill_dir>/graph.yaml`, `<skill_dir>/error-codes.md` from there) |
| `group_id` | Group id from `graph.yaml → edge_groups` (e.g. `GRP-SPO`) |
| `facts_paths` | Map `doc_type → absolute path to facts JSON`; `null` = the document is absent from the repository |
| `output_path` | Absolute path where you write the group's result JSON |

## Workflow

1. Read `<skill_dir>/graph.yaml`; select your group's edges.
2. Read every non-null facts file from `facts_paths` (small JSON; read whole).
3. For each edge of the group:
   a. Take `facts["<canonical section name>"]` on both sides (names as in graph.yaml, with spaces;
      key `version` for version_check; `presence`/`file_json_keys` per the edge's `fact` field).
   b. **A side is unavailable** (document `null` in `facts_paths`, or `value: null`): if that
      document/section is flagged `cond` or `conditional_doc: true` → not ERROR (WARNING/skip per
      conditionality). If absence can't be judged → **do not invent a mismatch**; skip unless the
      edge explicitly requires reporting the missing side.
   c. **Both sides present**: compare `value` per the `fact` semantics (lists — element-wise with
      case/whitespace normalization; `spo_list` for E-SPO-4 is coverage, see the edge's `rule`;
      digests — by meaning). Mismatch → one issue with the edge's `code`, naming **both** sides:
      file + section + line (from facts `position`).
   d. `symmetric: true` → one mismatch = one issue (not two mirrored ones).
   e. Honor the edge's `rule`, including anti-duplication (E-SPO-4 ↔ E-INC-4: one mismatch = one
      finding, CVAL-SPO takes precedence).
4. **GRP-VER**: collect `version` from every passed facts file; all values must match as strings;
   mismatch → `CVAL-VER`, paired against the first as reference (not a full pairwise matrix).
5. **Cross-doc notes** in the group (e.g. N-INST-1, N-SEC-1): check the note requirement against the
   involved sides' facts; violation → `CVAL-NOTE`; if not decidable from the available facts → skip,
   do not guess.
6. **Write `output_path`** (always, even with empty `issues`), then reply `written: <output_path>`.

## Output

> **All JSON field values are strings; `null` stays `null`.**

```json
{
  "group": "GRP-SPO",
  "issues": [
    {
      "code": "CVAL-SPO",
      "severity": "ERROR",
      "path": "documentation/documents/about/index.md",
      "message": "Перечень СПО не совпадает: «Системные требования» (`documentation/documents/about/index.md`, L20-31) ↔ «Чек-лист проверки корректности работы» (`documentation/documents/installation-guide/index.md`, L88-95); расхождение: в `about` есть `redis`, в `installation-guide` отсутствует.",
      "position": "20",
      "advice": "Добавить `redis` в чек-лист проверки корректности работы"
    }
  ]
}
```

`path` = document of the edge's side A. Issue fields and severity levels are as in the worker skill.
`message`/`advice` are written in Russian (technical terms in English).

## Rules

1. One edge-checker = one group; validate only your group's edges.
2. Read only: graph.yaml, error-codes.md, the passed facts files. No repository, no `get_single_file`,
   no other facts.
3. Compare only what's in facts. If a fact is empty/thin, that is not a mismatch; do not invent
   section content.
4. Every finding names both sides with coordinates (file + section + line).
5. One issue per mismatch (symmetric, anti-dupes per `rule`).
6. Finding text strictly per `<skill_dir>/error-codes.md`; Russian text, English identifiers.
7. Always write `output_path`; reply is one confirmation line.
