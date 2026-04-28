---
name: release-notes-generator
description: Use this skill to generate release notes from vulnerability reports and code change data. Triggers when user requests release notes, релизные заметки, or provides a release ID. Translates all descriptions to Russian and formats output as Markdown.
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
