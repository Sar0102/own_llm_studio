---
name: document-validator-orchestrator
description: Orchestrator for parallel documentation validation. Discovers every markdown file under documentation/documents, dispatches one worker PER FILE (parallel batches), then runs cross-document consistency checks from the workers' extracted facts and merges everything into consistency-validator.json.
---

# Document Validator — Orchestrator

## Overview

Coordinates documentation validation with **per-file** granularity. Each markdown file is handed
to its own worker (a section may hold many large files, so files are validated one at a time to
keep each worker's context bounded). The orchestrator then performs the **cross-document** checks
that no single-file worker can do — using the compact `facts` each worker extracted — and assembles
the final report.

Per-file validation logic (required sections, includes, references, notes, severity rules) lives
in the **worker** skill (`document-validator-worker`). The orchestrator owns discovery, dispatch,
cross-document consistency, and merge.

## Paths

| Purpose | Path |
|---|---|
| Discovery root | `documentation/documents` |
| Per-file results (workers write) | `{workspace_path}/tmp/document-validator/<file_id>.json` |
| Final report (orchestrator writes) | `{workspace_path}/reports/consistency-validator.json` |

`workspace_path` is `/docstorage/tmp/{{workflow.uid}}/`. `<file_id>` = relative path from `documents`
with `/` replaced by `__` (e.g. `developer-guide__index.md`).

## Workflow

### Phase 0: Discovery

1. Access the repository from the provided URL.
2. Navigate to `documentation/documents`.
3. **If `documentation/documents` does not exist — stop and report that no documents folder found.**
4. Recursively find every `.md` file under `documents` (`find documentation/documents -name '*.md'`).
5. Each file = one unit of work for one worker. Create `{workspace_path}/tmp/document-validator/`.

### Phase 1: Parallel Dispatch (one worker per file)

For each file, spawn a `document-validator-worker` subagent and pass:
- `file_path` — absolute path to the file.
- `doc_type` — inferred from the file's folder, if known (worker may re-infer).
- `file_id` — sanitized relative path.
- `output_path` — `{workspace_path}/tmp/document-validator/<file_id>.json`.

Run workers in **parallel batches**. Each worker validates exactly one file and writes its own
per-file result; workers never write the final report and never compare files.

### Phase 2: Join & Completeness

- Wait until every dispatched worker finished.
- Confirm a `<file_id>.json` exists for every dispatched file. Missing → retry that worker, or record:
  ```
  { "code": "CVAL-WORKER", "severity": "WARNING", "path": "documentation/documents/<file>", "message": "Воркер не вернул результат по файлу <file>" }
  ```

### Phase 3: Cross-Document Consistency (from facts)

Read all per-file results and use their `facts` (not full file text) to validate the graph's
consistency links. **Every cross-document issue must name file + section + line** (taken from the
facts' `*_position`), e.g. «версия указана в `front-matter`, строка 4».

| Link Type | Documents | What to Check |
|---|---|---|
| СПО (red) | `about` ⟷ `installation-guide` ⟷ `release-notes` | Перечень СПО / Системные требования совпадают |
| Логическая (blue) | `about` ⟷ `user-guide` ⟷ `administration-guide` | Сценарии использования |
| Логическая (blue) | `installation-guide` ⟷ `administration-guide` ⟷ `user-guide` | Параметры настройки |
| Логическая (blue) | `about` ⟷ `release-notes` ⟷ `test-plan` | Функции продукта |
| Логическая (blue) | `security-guide` ⟷ `administration-guide` ⟷ `user-guide` | Настройки безопасности |
| Логическая (blue) | `administration-guide` ⟷ `about` | Сценарии администрирования |
| Логическая (blue) | `developer-guide` ⟷ `agent-guide` | Общие сведения |
| Логическая (blue) | `release-notes` ⟷ `test-plan` | Исправленные ошибки |
| Включение (green) | `architecture` → `metadata` | Включение метаданных (db-models.json, deployment-units.json) |
| Ссылка (orange) | `architecture` → `deployment` | Диаграммы развертывания подключаются ссылкой |
| Зависимость (blue dotted) | `user-guide`, `developer-guide`, `agent-guide`, `deployment` | Наличие документа зависит от компонентного состава |

**Version consistency**: compare `facts.version` across documents and flag divergence
(`D-6.0.0` vs `6.0.0`) **with file + section + line for each side**.

Do **not** run the regression-tests ↔ «Основные функции» check (устаревшее — удалено).
Apply the same severity/conditionality rules as the worker (conditional → not ERROR; version-aware → SUGGESTION).

### Phase 4: Merge & Write

1. Concatenate all per-file `issues` + the cross-document issues.
2. Deduplicate identical issues (`code` + `path` + `message`).
3. Sort by severity (`ERROR` → `WARNING` → `SUGGESTION` → `INFO`), then by `path`.
4. Write the final report:

> **Все значения полей в JSON сериализуются как строки (тип `string`), даже если значение числовое — например `"priority": "15"`. Значение `null` остаётся `null`.**

```json
{
  "title": "Согласованность документации",
  "priority": "15",
  "issues": [
    {
      "code": "CVAL",
      "severity": "ERROR",
      "path": "documentation/documents/administration-guide/index.md",
      "message": "Несовпадение версий: 'D-6.0.0' (administration-guide, раздел Версия, стр. 4) против '6.0.0' (release-notes, раздел Версия, стр. 2).",
      "position": "4",
      "advice": "Привести к единому формату версии"
    }
  ]
}
```

Save to `{workspace_path}/reports/consistency-validator.json`. Issue fields, severity levels and
the `documentation/` path prefix are defined in the worker skill and preserved during merge.

## Rules

1. The orchestrator never validates a file's sections directly — it only dispatches and merges.
2. One worker = exactly one file (per-file granularity to bound context).
3. Cross-document checks use workers' `facts`, never full file contents.
4. Every cross-document/version issue names file + section + line.
5. Finalize only after all per-file results are present (or failures recorded).
6. The final report is written **only** to `{workspace_path}/reports/consistency-validator.json`.
7. Все значения полей в JSON — строки, даже числовые; `null` остаётся `null`.

## Constraints

1. Do not merge until all workers completed (or accounted for).
2. Do not modify issue contents during merge — only concatenate, dedupe, sort.
3. Do not scan anything outside `documentation/documents`.
