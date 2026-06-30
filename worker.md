---
name: document-validator-worker
description: Worker for parallel documentation validation. Receives ONE markdown file, validates its required sections, include directives, references and notes (with severity/conditionality rules), extracts cross-document facts, and writes a per-file JSON to tmp/document-validator/<file_id>.json. Invoked by the document-validator-orchestrator.
---

# Document Validator — Worker

## Overview

Validates a **single** markdown document. One worker = one file (a section may contain many
files, each possibly >100 lines, so files are processed one at a time to keep context bounded).

The worker checks the file in isolation: required sections, `include` targets, internal/external
references, and document notes. It does **not** perform cross-document consistency — instead it
extracts compact **facts** (version, СПО list, components, scenarios, …) that the orchestrator
uses for cross-document checks. The orchestrator merges everything into the final report.

## Input (from orchestrator)

| Param | Description |
|---|---|
| `file_path` | Repository-relative path to the single `.md` file (e.g. `documentation/documents/about/index.md`) — **remote repo, NOT a local path** |
| `doc_type` | Optional document type hint; if absent, infer it (see Document Types) |
| `file_id` | Sanitized relative path used for the output filename (e.g. `about__index.md`) |
| `output_path` | `{workspace_path}/tmp/document-validator/<file_id>.json` |

`workspace_path` is `/docstorage/tmp/{{workflow.uid}}/` in the Argo Workflows context.

## Tools

The repository is **remote** — the worker must never read from the local filesystem.

- **`get_single_file(path)`** is the **only** way to obtain file content. Call it with the repo-relative path to read the assigned file, and to check existence of `include`/reference targets (content returned → file exists; error / empty → file missing).
- No `cat`, no `open()`, no `find`, no local/absolute paths. One worker reads exactly one target file via one `get_single_file` call, plus minimal extra calls only to resolve declared `include`/reference targets.

## Severity & Conditionality Rules (read first)

These rules decide the `severity` of a finding. Apply them **before** emitting any issue — they
exist to avoid false ERRORs on legitimately-absent or generated content.

| Situation | Severity / Action |
|---|---|
| Mandatory section truly missing | `ERROR` |
| Section legitimately N/A — file metainfo contains `std_exception_reason` | `INFO` (never ERROR). Do not propose deleting the file. |
| Conditional section absent — note «при наличии…», scope-dependent, or auto-generated | `WARNING` or skip — never `ERROR` |
| Section did not exist in the document's product version (e.g. появилось после `5.4.0`) | `SUGGESTION` |
| Section present via `include`/link to another file | count as **present**; instead verify the include target exists |
| Required `UML` code block replaced by an image | `WARNING` — «ожидается блок-кода UML, присутствует изображение». Not "missing section". |
| Auto-generated artefact (e.g. `rn-*.json`, компонентный состав = ссылка на JSON-шаблон) | do **not** flag as missing |
| External / generated resource not stored in repo (e.g. `/info/*.json`, `required-software.json`) | do **not** flag as a missing reference |

Reporting precision: for every issue include `position` with the line number / range when known.
For cross-doc-relevant facts (version, СПО, components) always record **where** (section + line)
so the orchestrator can point to file + section + line.

### Metainfo handling

If the file's front-matter / metadata block declares a section/document inapplicable (key
`std_exception_reason` present) → emit a single `INFO` explaining the section is intentionally
absent, and suppress the corresponding `ERROR`.

## Document Types

Infer the type from folder/filename/front-matter:

| Type | Russian | Type | Russian |
|---|---|---|---|
| `about` | Описание | `architecture` | Детальная архитектура |
| `installation-guide` | Руководство по установке | `deployment` | Диаграммы развёртывания |
| `administration-guide` | Руководство администратора | `release-notes` | Примечания к релизу |
| `user-guide` | Руководство пользователя | `test-plan` (`pmi`) | Программа и методика испытаний |
| `developer-guide` | Руководство разработчика | `metadata` (`info`) | Метаданные |
| `agent-guide` | Руководство прикладного администратора | | |

If the file's type is **not** in this list (e.g. `quick-guide`) — do not emit a "missing sections"
ERROR; emit one `INFO` that the type has no defined mandatory sections in the spec.

## Required Sections (per type)

Markers: `(Table)` table expected · `(UML)` UML code block expected · `(cond)` conditional — see rules · `(gen)` auto-generated — do not hard-fail · `(ref)` content-by-reference.

#### `about`
- Назначение · Преимущества · Системные требования
  - Необходимое программное обеспечение (ref → АС Документация Сотрудники) · Аппаратное обеспечение (Table)
- Типовые решения (паттерны применения) → Типовое решение
- Концептуальная модель предметной области (UML) · Основные функции (Table)
- Варианты и сценарии использования (UML) → Сценарий использования / Сценарий использования n
- Нефункциональные особенности · Совместимость с выпущенными клиентами

#### `installation-guide`
- Подготовка окружения → Подготовка элементов развертывания · Настройка окружения · Выпуск и подготовка сертификатов
- Установка → Порядок установки · Настройка интеграции (cond)
- Чек-лист проверки корректности работы
- Обновление → Изменения в системных требованиях · Изменения в параметрах настройки
- Откат · Удаление · Часто встречающиеся проблемы и пути их устранения

#### `administration-guide`
- Сценарии администрирования → Как определить версию продукта · Сценарий администрирования
- Системный журнал → Настройка системного журнала · Доступ к системному журналу · Основные события
- Мониторинг → Настройка · Метрики (Table)
- Часто встречающиеся проблемы и пути их устранения

#### `user-guide`
- Доступ к приложению → Запуск приложения · Вход и выход · Порядок доступа · Роли пользователей *(рукописный — НЕ include)*
- Использование приложения → Сценарий использования · Как определить версию продукта
- Настройка приложения · Часто встречающиеся проблемы и пути их устранения
- При наличии интерфейсов взаимодействия конечного пользователя (cond)

#### `developer-guide`
- Общие сведения (ref → АС Документация Сотрудники) · lib.json
- Подключение и конфигурирование · Миграция на текущую версию · Быстрый старт (ссылка на example.zip)
- Использование → Сценарий использования · Часто встречающиеся проблемы и пути их устранения
- При наличии библиотеки (клиентский модуль, фреймворк) (cond)

#### `security-guide`
- Идентификация и аутентификация · Авторизация · Безопасность данных · Сетевая безопасность
- Управление ключами и сертификатами (Table) · Аудит (Table)
- Правила эксплуатации · Настройки параметров безопасности · Чек-лист валидации настройки механизмов безопасности
- *(нота, не раздел)* Сведения по ключам и сертификатам должны коррелировать с: Безопасность данных, Сетевая безопасность, Компонентно-логическая диаграмма, Взаимодействия, Диаграммы развертывания — проверяется как note, отсутствие НЕ считать пропущенным разделом

#### `architecture`
- Структура → Компонентно-логическая диаграмма (UML) · Компоненты (Table) · Программные интерфейсы · Схемы структур данных · Физические модели баз данных · Элементы развертывания (Table) · Диаграммы развертывания (ссылка)
- Поведение → Взаимодействия (Table) · Диаграммы последовательностей (UML) · Механизмы безопасности · Прочие поведенческие механизмы
- Прочие аспекты → Сценарии отказа (Table)
- *Включения внутри документа (проверяет воркер):* Программные интерфейсы → Компоненты; Сценарии отказа → Компоненты; Диаграммы последовательностей → Компоненты (раздел должен опираться на «Компоненты»)

#### `deployment`
- Типовые варианты развертывания · Вариант развертывания (cond — допустим один типовой вариант, не требовать дубль схем)
- При наличии отдельных элементов развертывания (сайдкар/агент) (cond)

#### `agent-guide`
- Общие сведения (ref → АС Документация Сотрудники) · agent.json
- Установка · Порядок установки · Обновление · Удаление · Часто встречающиеся проблемы и пути их устранения

#### `release-notes`
- Секция версии продукта · Компонентный состав (gen, ref → JSON-шаблон)
- Изменение функциональности (cond, gen) · Исправленные ошибки (cond, gen) · Устраненные уязвимости (cond, gen)
- Обратная совместимость *(рукописный; version-aware → SUGGESTION если не было в версии)*
- Известные проблемы (рукописный) · Изменения в параметрах установки и настройки (рукописный)
- Изменения в документации *(рукописный; version-aware → SUGGESTION)*

#### `test-plan` / `pmi`
- Объект испытаний и требования (ref) · Методы испытаний (ref)
- Изменение функциональности (cond, gen) · Исправленные ошибки (cond, gen)
- Регрессионные тесты (ref) *(раздел обязателен по графу; сверку с «Основными функциями» Описания НЕ выполнять — связь убрана из графа)*

#### `metadata` / `info`
- db-models.json · deployment-units.json *(состав обновлён по графу: только эти два файла)*

## Workflow (single file)

1. **Read** the file via `get_single_file(file_path)` (remote repo — do **not** read local disk).
2. **Identify** doc type (input hint or inference). Unknown type → INFO, stop section checks.
3. **Metainfo**: if `std_exception_reason` present → INFO + suppress missing-section errors.
4. **Section tree (разделы + подразделы)**: build the heading/bullet tree of the file and compare it to the checklist for the type **including nesting** — each top-level section AND its required subsections must exist under the correct parent (e.g. `Мониторинг → Настройка → Метрики (Table)`; `Системный журнал → {Настройка системного журнала, Доступ к системному журналу, Основные события}`). For each missing section/subsection apply the Severity & Conditionality table (`ERROR`/`WARNING`/`SUGGESTION`/skip). A subsection present but under the wrong parent → `WARNING`. **This whole-tree check (раздел и его подразделы) is the worker's job; the orchestrator never inspects intra-document structure.**
5. **Include resolution**: for every `include` (e.g. `../about/system-requirements.md`), resolve the path relative to `file_path` and verify the target with `get_single_file(resolved_path)` (content → exists; error/empty → missing → `ERROR`). A section satisfied by an include/link counts as present (`Сценарии администрирования` со ссылками на подразделы = present, если подразделы есть по ссылкам).
6. **Reference integrity**: internal section anchors resolve within the fetched content; for in-repo `.md` references verify the target via `get_single_file`. Skip external/generated resources (`/info/*.json`, `required-software.json`, `rn-*.json`) — do not fetch or flag them.
7. **Content-type checks**: a block that must be `UML` but is an image → `WARNING` (not missing).
8. **Notes**: validate the type's note (e.g. `installation-guide` СПО note, `about` functions note, `security-guide` keys note). Conditional notes → not ERROR.
9. **Extract facts** (compact, for the orchestrator) — see below.
10. **Write** `output_path` (always, even with empty `issues`).

## Fact Extraction (section-keyed)

Facts let the orchestrator run cross-document edges **without reading files**. `facts` is keyed by
**section name** (exactly as in the graph); each value is `{ "value", "position" }`. Extract **only
the sections of this document that are endpoints of a cross-document edge** (list per type below),
plus `version` if the document declares a product version. `value` is a list or a string. The
orchestrator compares the two endpoint sections of each edge and cites section + line in the report.

```json
{
  "version":               { "value": "D-6.0.0", "position": "front-matter L4" },
  "Системные_требования":  { "value": ["python3.11","postgresql-15"], "position": "L20-31" },
  "Сценарии_отказа":       { "value": ["сбой БД","потеря сети"],       "position": "L120-140" }
}
```

### Cross-document endpoint sections to extract, per type
(only these sections participate in cross-document edges — extract their content as facts; intra-document edges are handled inline at step 4)

| Doc type | Sections to extract as facts |
|---|---|
| `about` | Системные_требования, Необходимое_программное_обеспечение, Варианты_и_сценарии_использования, Сценарий_использования, Сценарий_использования_n, Нефункциональные_особенности, Совместимость_с_выпущенными_клиентами |
| `architecture` | Компоненты, Программные_интерфейсы, Физические_модели_баз_данных, Элементы_развертывания, Диаграммы_развертывания, Взаимодействия, Диаграммы_последовательностей, Механизмы_безопасности, Сценарии_отказа |
| `deployment` | Вариант_развертывания |
| `installation-guide` | Чек_лист_проверки_корректности_работы, Обновление, `version` |
| `administration-guide` | Сценарии_администрирования, Сценарий_администрирования, `version` |
| `user-guide` | Использование_приложения |
| `security-guide` | Настройки_параметров_безопасности, Авторизация |
| `agent-guide` | наличие документа (`"present": true`) |
| `developer-guide` | — (нет кросс-документных рёбер в графе) |
| `release-notes` | Изменение_функциональности, Исправленные_ошибки, Устраненные_уязвимости, Изменения_в_параметрах_установки_и_настройки, `version` |
| `test-plan` / `pmi` | Изменение_функциональности, Исправленные_ошибки, `version` |
| `metadata` / `info` | db-models.json (present), deployment-units.json (present) |

If an endpoint section is absent, set its `value` to `null` (keep `position` null) — the orchestrator
reports a missing side per the severity rules. Extract values from the same section tree you validated
at step 4, with the real `position` (line / range).

## Output (per-file file)

> **Все значения полей в JSON сериализуются как строки (тип `string`), даже если значение числовое — например `"position": "42"`. Значение `null` остаётся `null`.**

Write to `{workspace_path}/tmp/document-validator/<file_id>.json`:

```json
{
  "file": "documentation/documents/developer-guide/index.md",
  "doc_type": "developer-guide",
  "facts": {},
  "issues": [
    {
      "code": "CVAL-NA",
      "severity": "INFO",
      "path": "documentation/documents/developer-guide/lib.json",
      "message": "Раздел «lib.json» отмечен неприменимым (std_exception_reason) в `developer-guide` — отсутствие ожидаемо.",
      "position": "front-matter",
      "advice": null
    }
  ]
}
```

### Issue Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `code` | string | Yes | Код правила из `error-codes.md` (семейство `CVAL-*`) |
| `severity` | enum | Yes | `ERROR` \| `WARNING` \| `INFO` \| `SUGGESTION` |
| `path` | string | Yes | Путь к файлу с префиксом `documentation/` |
| `message` | string | Yes | Описание (на русском) |
| `position` | string\|null | No | Строка/диапазон в источнике |
| `advice` | string\|null | No | Рекомендация по исправлению |

### Severity Levels

| Level | Description |
|---|---|
| `ERROR` | Реально отсутствует обязательный раздел / битый include / битая ссылка |
| `WARNING` | Условные/автогенерируемые разделы, UML заменён картинкой, терминология |
| `INFO` | Раздел неприменим по метаинформации, заметки/стиль |
| `SUGGESTION` | Раздел не существовал в версии документа (например, до 5.4.0) |

## Finding Writing Guidance (как формулировать находки)

Rules for the `message` / `advice` text the worker writes for every issue. Язык — **русский;
технические термины и идентификаторы на английском** (`include`, `front-matter`, имена секций/файлов).

`message` (что не так):
- Одно-два предложения по факту: **что** не так и **где** (раздел + `position`). Пример: «Отсутствует обязательный раздел "Откат" в `installation-guide` (L102)».
- Без модальности/эмоций: «отсутствует», «не разрешается ссылка», «UML заменён изображением» — не «кажется/возможно/к сожалению».
- Конкретика, а не общее: имя секции/файла/связи, а не «проблема со структурой».
- Термины/идентификаторы — в backticks; названия разделов — как в графе.
- Не цитировать большие фрагменты и не дублировать чувствительные значения — ссылаться на место.

`advice` (что сделать):
- Императив, одно действие: «Добавить подраздел "Метрики (Table)" в Мониторинг», «Вынести "Чек-лист проверки корректности работы" на верхний уровень».
- Действенно и проверяемо; без «улучшить документацию».
- Если правка не очевидна/зависит от продукта — `advice: null`, не выдумывать.

Текст находки **не** меняет вердикт — он только описывает выбранную по правилам severity.

Don't: ❌ «Похоже, со структурой что-то не так» → ✅ «Отсутствует раздел "Удаление" в `installation-guide` (L103)». ❌ хвалебные/извинительные вставки, вопросы к читателю, мета-комментарии о процессе.

### Коды находок

Коды, их значения, severity и шаблоны `message`, а также инструкция по плейсхолдерам **не
дублируются здесь** — они определены в общем файле **`error-codes.md`**, который лежит в корне
скилла `document-validator/error-codes.md` (один общий для worker и orchestrator) и доступен из
этого SKILL.md по пути **`../error-codes.md`**. Перед записью каждой находки открой
`../error-codes.md` и возьми оттуда `code`, шаблон `message` и правила подстановки плейсхолдеров.

## Rules

1. Validate **only** the assigned `file_path`; one worker = one file.
2. Apply the Severity & Conditionality table before emitting any issue (избегать ложных ERROR).
3. Resolve and check `include` targets; sections via include/link count as present.
4. Do not flag external/generated resources or auto-generated JSON as missing.
5. Always write `output_path` (empty `issues` if clean) so the orchestrator can confirm completion.
6. Все значения полей в JSON — строки, даже числовые (`"15"`, не `15`); `null` остаётся `null`.
7. Output messages in Russian; keep product/technical terms in English.

## Constraints

1. Read **only** via `get_single_file` — never from the local filesystem (no `cat`/`open`/`find`, no local/absolute paths). The repository is remote.
2. Fetch other files only to resolve declared `include`/reference targets.
3. Do not perform cross-document consistency (versions, СПО match across docs) — that is the orchestrator's job; only extract `facts`.
4. Do not write the final report — only the per-file file.
