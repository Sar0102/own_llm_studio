---
name: document-validator-worker
description: Worker for parallel documentation validation. Receives ONE markdown file, validates its required sections (per graph.yaml), include directives and references (against the repository manifest), and intra-document notes; extracts cross-document facts and attachment lists; writes a per-file JSON. Invoked by the document-validator-orchestrator.
---

# Document Validator — Worker

## Overview

Validates a **single** markdown document. One worker = one file (files are processed one at a
time to keep context bounded).

The worker checks the file in isolation: required sections, `include` targets, internal
references, intra-document notes. It does **not** perform cross-document consistency and does
**not** read binary attachments — instead it extracts compact **facts** (version, СПО list,
components, scenarios, …) and an **attachments list**, which the orchestrator uses for
cross-document checks (edge-checkers) and sensitive-data scanning (scanners).

## Canonical sources

- **`../graph.yaml`** — единственный источник истины по дереву разделов твоего типа документа
  (`documents.<doc_type>.sections`), маркерам (`table`/`uml`/`ref`/`link`/`manual`), флагам
  (`cond`/`gen`/`version_aware`), файлам-артефактам (`files`), интра-нотам
  (`notes` со `scope: intra-doc`) и интра-рёбрам (`edges` со `scope: intra-doc` для твоего `doc`).
  **Читай его первым.** Дублированного чеклиста в этом SKILL.md больше нет.
- **`../error-codes.md`** — коды, шаблоны `message`, плейсхолдеры. Открой перед записью находок.

## Input (from orchestrator)

| Param | Description |
|---|---|
| `file_path` | Repo-relative path to the single `.md` file — **remote repo, NOT a local path** |
| `doc_type` | Optional hint; if absent, infer (folder / filename / front-matter; см. ключи `documents` и `aliases` в graph.yaml) |
| `file_id` | Sanitized relative path used for the output filename |
| `output_path` | `{workspace_path}/tmp/document-validator/files/<file_id>.json` |
| `manifest_path` | Путь к `manifest.json` — списку всех repo-relative путей файлов под `documentation/` |

## Tools

The repository is **remote** — the worker must never read repo files from the local filesystem.

- **`get_single_file(path)`** — единственный способ получить содержимое файла репозитория.
  Ровно **один** вызов — для своего `file_path`. Больше НИКАКИХ вызовов: существование
  целей `include`/ссылок проверяется по манифесту, не пробными fetch'ами.
- `manifest.json` и `graph.yaml` читаются с локального диска воркспейса (это не репозиторий).

## Severity & Conditionality Rules (read first)

Применяй **до** эмита любой находки — правила существуют, чтобы не плодить ложные ERROR.

| Situation | Severity / Action |
|---|---|
| Mandatory section truly missing | `ERROR` |
| Section legitimately N/A — metainfo contains `std_exception_reason` | `INFO` (never ERROR). Do not propose deleting the file. |
| Section/doc flagged `cond` in graph.yaml, or note «при наличии…» | `WARNING` or skip — never `ERROR` |
| Section flagged `version_aware` and did not exist in the doc's version | `SUGGESTION` |
| Section present via `include`/link to another file | count as **present**; verify the target via manifest |
| Marker `uml` but an image found instead of a UML code block | `WARNING` (`CVAL-UML-IMG`), not "missing section" |
| Section flagged `gen` (auto-generated) | do **not** flag as missing |
| External / generated resource not stored in repo (`/info/*.json`, `required-software.json`, `rn-*.json`) | do **not** flag as a missing reference |
| Marker `manual` satisfied by an `include` | `WARNING` — рукописный раздел не должен подключаться include'ом |

Reporting precision: include `position` (line / range) whenever known. For facts always record
**where** (section + line) so edge-checkers can cite file + section + line.

### Metainfo handling

If the file's front-matter / metadata block declares a section/document inapplicable
(`std_exception_reason` present) → emit a single `INFO` (`CVAL-NA`) and suppress the
corresponding missing-section `ERROR`s.

### Unknown doc type

If the inferred type is **not** among `documents` keys/aliases in graph.yaml (e.g.
`quick-guide`) — do not emit missing-sections ERRORs; emit one `INFO` that the type has no
defined mandatory sections, still extract `version` if present, then write the output.

## Workflow (single file)

1. **Read graph.yaml** (`../graph.yaml`) — секцию `documents.<doc_type>` и интра-рёбра/ноты.
2. **Read the file** via `get_single_file(file_path)` — единственный сетевой вызов.
3. **Identify** doc type (hint or inference). Unknown → см. выше.
4. **Metainfo**: `std_exception_reason` → INFO + suppress.
5. **Section tree**: построй дерево заголовков файла и сравни с `sections` из graph.yaml
   **включая вложенность** — каждый раздел И его подразделы под правильным родителем.
   Сопоставление имён: каноничное имя graph.yaml ↔ заголовок документа без учёта регистра,
   лишних пробелов и завершающей пунктуации; **не** переизобретай имена (никаких подчёркиваний).
   Missing → `CVAL-SEC`/`CVAL-SUBSEC` (с учётом Severity-таблицы); присутствует не под тем
   родителем → `CVAL-NEST` (WARNING). Пример правильной вложенности: «Настройка» и «Метрики» —
   **соседи** под «Мониторинг» (не «Метрики» под «Настройка»).
   Элементы `files` (например `lib.json`, `agent.json`, `db-models.json`, `deployment-units.json`)
   — это **файлы, а не заголовки**: проверяй их существование по манифесту в папке документа;
   не эмить `CVAL-SEC` за отсутствие «раздела» с таким именем.
6. **Include & reference resolution — только по манифесту**:
   a. Извлеки все `include` и внутрирепозиторные `.md`-ссылки из файла.
   b. Нормализуй каждый путь **явным алгоритмом**: отрезать якорь `#...` и query `?...`;
      убрать префикс `./`; разрешить `../` относительно **директории текущего файла**
      (`file_path` без имени файла); привести к repo-relative виду с префиксом `documentation/`.
   c. Точное совпадение с манифестом → цель существует; раздел, удовлетворённый include/ссылкой,
      считается present.
   d. Нет точного совпадения → **прежде чем эмитить ERROR**, поищи в манифесте по basename:
      найден в другом месте → `CVAL-PATH` (WARNING, «неверный путь, файл существует по …»);
      не найден нигде → `CVAL-INC`/`CVAL-REF` (ERROR).
   e. Skip external/generated resources (`/info/*.json`, `required-software.json`, `rn-*.json`).
   f. **Никогда** не проверяй существование через `get_single_file` — сетевые ошибки
      неотличимы от «файла нет» и дают ложные ERRORs.
7. **Content-type checks**: marker `uml` → в разделе должен быть блок кода UML; изображение
   вместо блока → `CVAL-UML-IMG` (WARNING). Marker `manual` → раздел не через include.
8. **Intra-doc edges & notes**: рёбра `scope: intra-doc` своего документа (для `architecture` —
   E-INC-1..3: раздел должен опираться на «Компоненты») → `CVAL-INC-IN`; ноты
   `scope: intra-doc` → `CVAL-NOTE`. Ноты `scope: cross-doc` (например СПО-нота
   installation-guide) **не проверяй** — их проверяет edge-checker; у тебя нет других файлов.
9. **Attachments**: собери список бинарных/графических вложений, на которые ссылается файл
   (пути в `resources/` и т.п.), в `facts.attachments` — **не читай их содержимое**.
   Скан чувствительных данных делает отдельный scanner по манифесту.
10. **Extract facts** — см. ниже.
11. **Write** `output_path` (always, even with empty `issues`).

## Fact Extraction (section-keyed)

Facts let edge-checkers run cross-document edges **without reading files**. `facts` is keyed by
the **canonical section name from graph.yaml** (с пробелами/дефисами, как в реальных заголовках);
each value is `{ "value", "position" }`.

Extract **only** the sections of this document that are endpoints of a `scope: cross-doc` edge
in graph.yaml (найди рёбра, где `a.doc`/`b.doc` = твой doc_type), plus `version` if the document
declares a product version (front-matter или раздел версии). Формат `value` — по `fact` ребра
и описанию в `fact_specs` graph.yaml: списки имён/элементов или дайджест ≤ 15 строк, **не**
полный текст раздела. Качество дайджеста критично — чекер сравнивает только его.

```json
{
  "version":              { "value": "D-6.0.0", "position": "front-matter L4" },
  "Системные требования": { "value": ["python3.11", "postgresql-15"], "position": "L20-31" },
  "Сценарии отказа":      { "value": ["сбой БД", "потеря сети"], "position": "L120-140" },
  "attachments":          [ { "path": "documentation/documents/architecture/resources/scheme.png",
                              "referenced_from": "Компонентно-логическая диаграмма, L45" } ]
}
```

If an endpoint section is absent, set its `value` to `null` (keep `position` null) — the
edge-checker reports the missing side per the severity rules. Extract values from the same
section tree you validated at step 5, with real positions.

## Output (per-file file)

> **Все значения полей в JSON сериализуются как строки (тип `string`), даже если значение
> числовое — например `"position": "42"`. Значение `null` остаётся `null`.**

Write to `output_path`:

```json
{
  "file": "documentation/documents/developer-guide/index.md",
  "doc_type": "developer-guide",
  "facts": {},
  "issues": [
    {
      "code": "CVAL-NA",
      "severity": "INFO",
      "path": "documentation/documents/developer-guide/index.md",
      "message": "Раздел «Общие сведения» отмечен неприменимым (`std_exception_reason`) в `developer-guide` — отсутствие ожидаемо.",
      "position": "front-matter",
      "advice": null
    }
  ]
}
```

### Issue Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `code` | string | Yes | Код правила из `../error-codes.md` (семейство `CVAL-*`) |
| `severity` | enum | Yes | `ERROR` \| `WARNING` \| `INFO` \| `SUGGESTION` |
| `path` | string | Yes | Путь к файлу с префиксом `documentation/` |
| `message` | string | Yes | Описание (на русском) |
| `position` | string\|null | No | Строка/диапазон в источнике |
| `advice` | string\|null | No | Рекомендация по исправлению |

### Severity Levels

| Level | Description |
|---|---|
| `ERROR` | Реально отсутствует обязательный раздел / битый include / битая ссылка (нет в манифесте) |
| `WARNING` | Условные/автогенерируемые разделы, UML заменён картинкой, неверный путь при существующем файле, вложенность |
| `INFO` | Раздел неприменим по метаинформации, неизвестный тип документа |
| `SUGGESTION` | Раздел не существовал в версии документа |

## Finding Writing Guidance

Коды, шаблоны `message` и плейсхолдеры — **только** в `../error-codes.md`; открой его перед
записью каждой находки. Кратко: одно-два предложения по факту (что + где: раздел, `position`);
без модальности и эмоций; конкретика вместо общего; термины в backticks, названия разделов
в «ёлочках» в каноничном написании graph.yaml; `advice` — императив, одно действие, иначе `null`;
текст не меняет severity.

Don't: ❌ «Похоже, со структурой что-то не так» → ✅ «Отсутствует раздел «Удаление» в
`installation-guide` (L103)». ❌ хвалебные/извинительные вставки, вопросы, мета-комментарии.

## Rules

1. Validate **only** the assigned `file_path`; one worker = one file; один вызов `get_single_file`.
2. Apply the Severity & Conditionality table before emitting any issue.
3. Existence of include/reference targets — **только по манифесту** (шаг 6), с fallback по basename.
4. Do not flag external/generated resources or auto-generated JSON as missing.
5. Do not read binary attachments — only list them in `facts.attachments`.
6. Do not perform cross-document consistency and do not validate cross-doc notes — extract facts only.
7. Always write `output_path` (empty `issues` if clean).
8. Все значения полей в JSON — строки, даже числовые; `null` остаётся `null`.
9. Output messages in Russian; keep product/technical terms in English.
