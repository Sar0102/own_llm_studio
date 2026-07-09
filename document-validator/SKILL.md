---
name: document-validator-orchestrator
description: Orchestrator for parallel documentation validation. Discovers every markdown file under documentation/documents, builds a repository manifest, dispatches one worker PER FILE (parallel batches), dispatches edge-checkers for cross-document consistency groups from graph.yaml, dispatches sensitive-data scanners for resources/ images, and merges everything into consistency-validator.json.
---

# Document Validator — Orchestrator

## Overview

Coordinates documentation validation with **per-file** granularity and a **constant-size context**:
the orchestrator never reads document content, never reads full facts files, and never compares
sections itself. It only discovers, dispatches, tracks, and merges.

Division of labour:

| Agent | Does | Context |
|---|---|---|
| **worker** (`worker/SKILL.md`) | one file: sections, includes, refs, notes(intra), facts | 1 файл + graph.yaml |
| **edge-checker** (`edge-checker/SKILL.md`) | one edge group: cross-doc consistency from facts | 2–5 маленьких facts JSON |
| **scanner** (`scanner/SKILL.md`) | one `resources/` file: sensitive data | 1 файл + sensitive-data.md |
| **orchestrator** (this) | discovery, manifest, dispatch, doc-existence edges, merge | списки путей + статусы |

## Canonical sources (в корне скилла)

- **`./graph.yaml`** — единственный источник истины: типы документов, деревья разделов,
  маркеры/флаги, ноты и **все** рёбра консистентности (с `scope`, `code`, `group`).
  Если что-либо в этом SKILL.md противоречит `graph.yaml` — прав `graph.yaml`.
- **`./error-codes.md`** — коды находок, шаблоны `message`, правила плейсхолдеров.
- **`./sensitive-data.md`** — словарь чувствительной информации для скана `resources/`.

PlantUML-диаграммы больше нет: она была источником неоднозначностей (вложенность через
`___`, семантика через цвет, алиасы узлов). Не восстанавливать её и не опираться на память о ней.

## Paths

| Purpose | Path |
|---|---|
| Discovery root | `documentation/documents` |
| Repository manifest (orchestrator writes) | `{workspace_path}/tmp/document-validator/manifest.json` |
| Per-file results (workers write) | `{workspace_path}/tmp/document-validator/files/<file_id>.json` |
| Edge-group results (edge-checkers write) | `{workspace_path}/tmp/document-validator/edges/<group_id>.json` |
| Scanner results (scanners write) | `{workspace_path}/tmp/document-validator/scans/<file_id>.json` |
| Final report (orchestrator writes) | `{workspace_path}/reports/consistency-validator.json` |

`workspace_path` = `/docstorage/tmp/{{workflow.uid}}/`. `<file_id>` = путь относительно
`documents` с `/` → `__` (например `developer-guide__index.md`, `architecture__resources__scheme.png`).

## Workflow

### Phase 0: Discovery & Manifest

1. Use the remote repository integration (source-control tool) for the provided URL — **do not clone locally**.
2. Enumerate the **full file tree** under `documentation/` via the repository listing call
   (one remote listing, no file contents). If `documentation/documents` does not exist — stop
   and report that no documents folder was found.
3. Write **`manifest.json`**: плоский JSON-массив всех repo-relative путей файлов под
   `documentation/`. Манифест — единственный способ проверки существования файлов для всех
   субагентов (никаких «пробных» `get_single_file` ради проверки существования).
4. From the manifest derive two work lists:
   - **doc files**: every `.md` under `documentation/documents` → по одному worker.
   - **scan targets**: every file under any `resources/` folder (`**/resources/*`) with
     extensions `.png .jpg .jpeg .gif .bmp .webp .svg .drawio` → **dedupe by path** →
     по одному scanner. Один и тот же файл, на который ссылаются несколько документов,
     сканируется ровно один раз.
5. Create the tmp directories (`files/`, `edges/`, `scans/`).

### Phase 1: Parallel Dispatch — workers (one per .md file)

For each doc file spawn a `document-validator-worker` and pass:
- `file_path` — repo-relative путь (remote; worker читает через `get_single_file`).
- `doc_type` — inferred from the folder, if known (worker may re-infer).
- `file_id`, `output_path` — `.../files/<file_id>.json`.
- `manifest_path` — путь к `manifest.json` (для проверки include/ссылок).

Run in **parallel batches**. Workers never write the final report and never compare files.

### Phase 1b: Parallel Dispatch — scanners (one per resources file)

For each scan target spawn a `document-validator-scanner` and pass:
- `file_path`, `file_id`, `output_path` — `.../scans/<file_id>.json`.

Scanners can run in the same batch wave as workers — they are independent.
Files > 5 MB are skipped by the scanner itself (`CVAL-SENS-SKIP`).

### Phase 2: Join & Completeness

- Wait until every dispatched worker and scanner finished.
- Confirm the output JSON exists for every dispatched unit. Missing → retry once, or record:
  ```
  { "code": "CVAL-WORKER", "severity": "WARNING", "path": "documentation/documents/<file>",
    "message": "Субагент не вернул результат по `<file>`." }
  ```
- Build the **facts index**: `doc_type → путь к facts-файлу` (только маппинг путей;
  содержимое facts оркестратор НЕ читает).

### Phase 3a: Doc-existence edges (orchestrator, по манифесту)

Проверяются рёбра `graph.yaml` со `scope: doc-existence` — им не нужны facts-сравнения,
только манифест плюс один флаг присутствия триггер-раздела из facts-файла architecture
(единственное точечное чтение: одно маленькое поле `presence`):

- `E-DEP-1`, `E-DEP-2` → `CVAL-DEP`: триггер-раздел непуст, а требуемый документ
  отсутствует в манифесте → WARNING (документ опционален, поэтому не ERROR).
- `E-LINK-1` → `CVAL-LINK`: раздел-ссылка architecture ведёт в `deployment`,
  которого нет в манифесте → ERROR.

### Phase 3b: Parallel Dispatch — edge-checkers (one per edge group)

For each group in `graph.yaml → edge_groups` (GRP-SPO, GRP-DEPLOY, GRP-ARCH, GRP-SCEN,
GRP-RN, GRP-DEP, GRP-VER) spawn a `document-validator-edge-checker` and pass:
- `group_id`.
- `facts_paths` — map `doc_type → путь к facts JSON` только для docs этой группы.
  Если документа нет в репозитории — передай `null`; чекер применит правила
  условности (conditional doc → не ERROR).
- `output_path` — `.../edges/<group_id>.json`.

Чекер читает `../graph.yaml` (свою группу), `../error-codes.md` и только переданные
facts-файлы. Кросс-документные ноты (`scope: cross-doc` в graph.yaml) проверяет чекер
группы, в которую нота включена.

### Phase 4: Merge & Write

1. Concatenate issues из всех трёх источников: `files/*.json` + `edges/*.json` + `scans/*.json`
   + собственные находки Phase 2/3a.
2. Deduplicate identical issues (`code` + `path` + `message`).
3. Sort by severity (`ERROR` → `WARNING` → `SUGGESTION` → `INFO`), then by `path`.
4. Write the final report:

> **Все значения полей в JSON сериализуются как строки (тип `string`), даже если значение
> числовое — например `"priority": "15"`. Значение `null` остаётся `null`.**

```json
{
  "title": "Согласованность документации",
  "priority": "15",
  "issues": [
    {
      "code": "CVAL-VER",
      "severity": "ERROR",
      "path": "documentation/documents/administration-guide/index.md",
      "message": "Несовпадение версий: «D-6.0.0» (`administration-guide`, Версия, L4) ≠ «6.0.0» (`release-notes`, Версия, L2).",
      "position": "4",
      "advice": "Привести к единому формату версии"
    }
  ]
}
```

Save **only** to `{workspace_path}/reports/consistency-validator.json`. Issue fields,
severity levels and the `documentation/` path prefix are defined in the worker skill and
preserved during merge. Merge — чисто механическая операция (конкатенация/дедуп/сортировка);
при возможности выноси её в детерминированный шаг DAG вместо LLM.

## Rules

1. The orchestrator never reads document content and never reads facts files целиком —
   only path lists, statuses, and single `presence` flags for Phase 3a.
2. One worker = exactly one file; one scanner = exactly one file; one edge-checker = exactly one group.
3. File existence is checked **only** against `manifest.json` — никаких пробных fetch'ей.
4. Every cross-document/version issue names file + section + line (это делает чекер; оркестратор не переписывает).
5. Finalize only after all subagents are present (or failures recorded as `CVAL-WORKER`).
6. Do not modify issue contents during merge — only concatenate, dedupe, sort.
7. Do not scan anything outside `documentation/`.
8. Все значения полей в JSON — строки, даже числовые; `null` остаётся `null`.

## Finding Writing Guidance

Правила формулировок (`message`/`advice`), коды, шаблоны и плейсхолдеры определены в
**`./error-codes.md`** — единственном месте. Перед записью каждой собственной находки
(Phase 2/3a) открой его и возьми оттуда `code`, шаблон и правила подстановки.
Кратко: русский язык, термины на английском; конкретика (файл + раздел + строка);
без модальности и эмоций; для кросс-док находок — обе стороны с координатами;
текст находки не меняет severity.
