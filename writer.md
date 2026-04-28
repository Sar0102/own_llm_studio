---
name: release-notes-generator
description: description: |
  Генерация release notes (релизных заметок) для релиза в виде структурированного markdown-документа на русском языке.
  
  ОБЯЗАТЕЛЬНО используй этот скилл когда пользователь:
  - Просит сформулировать, подготовить, сделать, написать, создать, сгенерировать релиз или release notes
  - Спрашивает что вошло в релиз, что изменилось в релизе, что нового в версии
  - Просит релизные заметки, описание релиза, changelog, список изменений
  - Указывает идентификатор релиза в формате BD.XXX (например BD.298), BSSI X.X.X-XXXX, v1.X.X
  - Использует слова: релиз, release, release notes, релизные заметки, changelog, версия, version
  
  Примеры запросов которые ОБЯЗАТЕЛЬНО триггерят этот скилл:
  - "Сформулируй релиз для BD.298"
  - "Сформулируй release notes для BD.298"
  - "Подготовь релизные заметки для BD.298"
  - "Сделай релиз BD.298"
  - "Что вошло в релиз BD.298"
  - "Опиши изменения в релизе BD.298"
  - "Generate release notes for BD.298"
  - "Release notes BD.298"
  - "Релиз для BSSI 4.8.1-1320"
  - "Changelog для версии v1.2.0"
  
  Скилл выполняет полный workflow: вызывает tools для сбора данных о задачах, 
  уязвимостях (CVE), и pull requests релиза. Классифицирует их по типам 
  (устранённые уязвимости, исправленные ошибки, изменение функциональности).
  Переводит описания на русский язык. Формирует итоговый markdown-документ 
  по обязательному шаблону с таблицами по разделам.
  
  Внутри скилла подробные инструкции с фазами: Phase 1 — сбор данных через tools,
  Phase 2 — классификация и форматирование. Без выполнения этих фаз результат
  будет неполным.

allowed-tools: get_unit_list, get_unit_details, get_unit_pull_requests
---

# Release Notes Generator

## Overview

Generates structured release notes for a release by collecting tasks,
vulnerabilities, and pull request data via tools, classifying tasks
by type, translating all descriptions to Russian, and formatting
the result as Markdown.

## When to use

- User mentions "release notes", "релизные заметки", or "version notes"
- User provides a release ID
- User asks to summarize what changed in a release

## Workflow

The workflow has two strict phases. Do not produce any output text
during Phase 1 — only call tools.

### Phase 1: Data collection

Execute these steps in order. Do not skip or reorder.

**Step 1. Get task list**

Call `get_unit_list` for the release.

For each unit, save: `code`, `summary`, `description.content`, `type`, `source`.

From the first record, extract the field `Версия` and save it as `release_id`.

**Step 2. Get unit details**

For each unit code from Step 1, call `get_unit_details`.

Extract two related types:

- `type="sber_component"` → `value[].name` (as-is) → component code.
  Example: `"SRGE"`.

- `type="version"` → `value[].name` split into two parts:
  - Component name: strip trailing version pattern `\d+[\d.]+\d+[\w-]*`.
    Example: `"Platform V Frontend High Load 4.3.9.6"` → `"Platform V Frontend High Load"`.
  - Version: extract only the version pattern `\d+[\d.]+\d+[\w-]*`.
    Example: `"Platform V Frontend High Load 4.3.9.6"` → `"4.3.9.6"`.

Pair each `type="version"` `value[]` with the corresponding `type="sber_component"` `value[].name`
by their order index. Each row contains: code, component name, version.

**Step 3. Get pull requests**

For each unit code from Step 1, call `get_unit_pull_requests`.

Save: PR descriptions, links, and changes.

**Empty result handling**

If steps 1–3 return no data, output exactly:

> Данные для формирования release notes не найдены.

Then stop. Do not proceed to Phase 2.

### Phase 2: Generate report

Start this phase only after all Phase 1 tool calls are complete.

All output must be in Russian. Technical identifiers (ticket codes,
component codes, CVE identifiers) remain unchanged.

#### Task classification

Apply rules in priority order. The first match wins.

**Устраненные уязвимости** — only entries with a CVE identifier:
- `STS` with `type=BUG_КБ`
- `SBTSUPPORT` where `name` matches `CVE-\d+-\d+`

**Исправленные ошибки**:
- `TSK` (all)
- `SBTSUPPORT` where `name` does NOT match `CVE-\d+-\d+`
- `STS` where `type=Bug` AND `type≠BUG_КБ`

**Изменение функциональности**:
- `STS` where `type≠Bug`
- `CRPV` excluding Citadel tasks

**Citadel exclusion** — exclude entirely if `CRPV` `name` matches any of:
- `Реализовать требование .* стандарта`
- `Пройти ручную проверку на соответствие требованию .* стандарта`
- `Реализовать стандарт`
- `Пройденные требования стандарта`
- `Пройденные требования по стандарту`
- `Нарушение стандарта`

#### Output rules

- If a section has no tasks, omit both the header and the table entirely.
- Use the template from `templates/release-notes.md`.

## Critical requirements

| Requirement | Specification |
|---|---|
| Data completeness | Obtain data for all tasks and all pull requests. Skipping is unacceptable. |
| Russian language | All descriptions and summaries must be translated to Russian. |
| Format | Output strictly in Markdown with proper headers and tables. |
| Dynamic structure | No records → omit both header and table. |
| Step order | Execute Phase 1 steps strictly 1 → 2 → 3. |

## Constraints

1. Do not output descriptions or summaries in English, except codes and identifiers.
2. Do not add commentary outside the template.
3. Do not modify column headers.
4. Do not translate ticket identifiers or component codes.
5. Omit a section entirely if it has no data. Do not insert "no data" rows.
6. Do not use H3 (`###`) for main sections. Use H1 (`#`) for the title and H2 (`##`) for sections.
7. Do not generate any text before all Phase 1 tool calls are complete.

## Example

See `examples/output.md` for a reference of the expected format.
