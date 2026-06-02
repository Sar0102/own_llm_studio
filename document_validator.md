-----

## name: document-validator

description: Validates technical documentation (about, installation-guide, architecture, etc.) for consistency, completeness, and correctness. Use when the user mentions validate / validation / проверка / валидация, asks to check document consistency (консистентность), or to verify documentation completeness against the architecture graph.

# Document Validator

## Overview

Validates technical documentation for consistency, completeness, and correctness.
Checks cross-references between documents, verifies required sections exist,
and ensures content alignment across the documentation set.

## When to use

- User mentions “validate”, “validation”, “проверка”, “валидация”
- User asks to check document consistency (“консистентность”)
- User requests to verify documentation completeness
- User wants to find missing or inconsistent sections
- User provides document structure or asks to verify against architecture

## Document Types

The validator recognizes these document types:

|Document Type         |Russian Name                          |Key Sections                                                                                                       |
|----------------------|--------------------------------------|-------------------------------------------------------------------------------------------------------------------|
|`about`               |Описание                              |Назначение, Преимущества, Системные требования, Основные функции                                                   |
|`installation-guide`  |Руководство по установке              |Подготовка, Установка, Обновление, Откат, Удаление                                                                 |
|`administration-guide`|Руководство администратора            |Сценарии администрирования, Мониторинг, Настройка, Журналы                                                         |
|`user-guide`          |Руководство пользователя              |Доступ, Запуск, Использование, Настройка                                                                           |
|`developer-guide`     |Руководство разработчика              |Подключение, Конфигурирование, Миграция, Использование                                                             |
|`agent-guide`         |Руководство прикладного администратора|Установка, Обновление, Удаление                                                                                    |
|`security-guide`      |Руководство по безопасности           |Идентификация, Авторизация, Безопасность данных, Аудит                                                             |
|`architecture`        |Детальная архитектура                 |Структура, Компоненты, Схемы данных, Развёртывание                                                                 |
|`deployment`          |Диаграммы развёртывания               |Типовые варианты, Варианты развёртывания                                                                           |
|`release-notes`       |Примечания к релизу                   |Изменения, Исправленные ошибки, Известные проблемы                                                                 |
|`test-plan`           |Программа и методика испытаний (`pmi`)|Объект испытаний, Методы, Регрессионные тесты                                                                      |
|`metadata`            |Метаданные (`info`)                   |dbmodels, software-product-integration-cases.json, platform-component-integration-cases.json, deployment-units.json|

## Validation Rules

### 1. Cross-Document Consistency

Check that related sections across documents are consistent. The following table defines all required consistency checks:

|Section / Content          |Documents to Check                                          |Link Type                |
|---------------------------|------------------------------------------------------------|-------------------------|
|Системные требования       |`about`, `installation-guide`, `release-notes`              |СПО (red)                |
|Сценарии использования     |`about`, `user-guide`, `administration-guide`               |Логическая (blue)        |
|Параметры настройки        |`installation-guide`, `administration-guide`, `user-guide`  |Логическая (blue)        |
|Функции продукта           |`about`, `release-notes`, `test-plan`                       |Логическая (blue)        |
|Компоненты                 |`architecture`, `deployment`, `installation-guide`          |Логическая (blue)        |
|Диаграммы развёртывания    |`architecture`, `deployment`                                |Ссылка (orange)          |
|Настройки безопасности     |`security-guide`, `administration-guide`, `user-guide`      |Логическая (blue)        |
|Сценарии администрирования |`administration-guide`, `about`                             |Логическая (blue)        |
|Общие сведения             |`developer-guide`, `agent-guide`                            |Логическая (blue)        |
|Исправленные ошибки        |`release-notes`, `test-plan`                                |Логическая (blue)        |
|Метаданные (dbmodels, JSON)|`architecture`, `metadata`                                  |Включение (green)        |
|Условные документы         |`user-guide`, `developer-guide`, `agent-guide`, `deployment`|Зависимость (blue dotted)|

### Link Types (from Legend)

|Type       |Description                                                   |Visual           |
|-----------|--------------------------------------------------------------|-----------------|
|СПО        |Перечень программного обеспечения должен совпадать            |Red dashed       |
|Логическая |Логические связи и консистентность контента                   |Blue dashed/solid|
|Включение  |Включение части контента одного раздела в другой              |Green dashed     |
|Ссылка     |Контент в виде ссылки                                         |Orange solid     |
|Зависимость|Наличие документов и разделов зависит от компонентного состава|Blue dotted      |

### 2. Required Sections Validation

Each document type must have mandatory sections as defined in the graph:

#### `about` (Описание)

- [ ] Назначение
- [ ] Преимущества
- [ ] Системные требования
  - [ ] Необходимое программное обеспечение (ссылка на АС Документация Сотрудники)
  - [ ] Аппаратное обеспечение (Table)
- [ ] Типовые решения (паттерны применения)
  - [ ] Типовое решение
- [ ] Концептуальная модель предметной области (UML)
- [ ] Основные функции (Table)
- [ ] Варианты и сценарии использования (UML)
  - [ ] Сценарий использования
  - [ ] Сценарий использования n
- [ ] Нефункциональные особенности
- [ ] Совместимость с выпущенными клиентами

#### `installation-guide` (Руководство по установке)

- [ ] Подготовка окружения
  - [ ] Подготовка элементов развертывания
  - [ ] Настройка окружения
  - [ ] Выпуск и подготовка сертификатов
- [ ] Установка
  - [ ] Порядок установки
  - [ ] Настройка интеграции
  - [ ] Чек-лист проверки корректности работы
- [ ] Обновление
  - [ ] Изменения в системных требованиях
  - [ ] Изменения в параметрах настройки
- [ ] Откат
- [ ] Удаление
- [ ] Часто встречающиеся проблемы и пути их устранения

#### `administration-guide` (Руководство администратора)

- [ ] Сценарии администрирования
  - [ ] Как определить версию продукта
  - [ ] Сценарий администрирования
- [ ] Системный журнал
  - [ ] Настройка системного журнала
  - [ ] Доступ к системному журналу
  - [ ] Основные события
- [ ] Мониторинг
- [ ] Настройка
  - [ ] Метрики (Table)
- [ ] Часто встречающиеся проблемы и пути их устранения

#### `user-guide` (Руководство пользователя)

- [ ] Доступ к приложению
- [ ] Запуск приложения
- [ ] Вход и выход
- [ ] Порядок доступа
- [ ] Роли пользователей (Include)
- [ ] Использование приложения
  - [ ] Сценарий использования
- [ ] Как определить версию продукта
- [ ] Настройка приложения
- [ ] Часто встречающиеся проблемы и пути их устранения
- [ ] При наличии у продукта интерфейсов взаимодействия конечного пользователя (веб-консоль, приложение, утилита командной строки)

#### `developer-guide` (Руководство разработчика)

- [ ] Общие сведения (АС Документация Сотрудники)
- [ ] lib.json
- [ ] Подключение и конфигурирование
- [ ] Миграция на текущую версию
- [ ] Быстрый старт (ссылка на example.zip)
- [ ] Использование
  - [ ] Сценарий использования
- [ ] Часто встречающиеся проблемы и пути их устранения
- [ ] При наличии у продукта библиотеки (клиентский модуль, фреймворк)

#### `security-guide` (Руководство по безопасности)

- [ ] Идентификация и аутентификация
- [ ] Авторизация
- [ ] Безопасность данных
- [ ] Сетевая безопасность
- [ ] Управление ключами и сертификатами (Table)
- [ ] Аудит (Table)
- [ ] Правила эксплуатации
- [ ] Настройки параметров безопасности
- [ ] Чек-лист валидации настройки механизмов безопасности
- [ ] Сведения по ключам и сертификатам должны коррелировать с разделами:
  - Безопасность данных
  - Сетевая безопасность
  - Компонентно-логическая диаграмма
  - Взаимодействия
  - Диаграммы развертывания

#### `architecture` (Детальная архитектура)

- [ ] Структура
- [ ] Компонентно-логическая диаграмма (UML)
- [ ] Компоненты (Table)
- [ ] Программные интерфейсы
- [ ] Схемы структур данных
- [ ] Физические модели баз данных (Table)
- [ ] Элементы развертывания (Table)
- [ ] Диаграммы развертывания (ссылка)
- [ ] Диаграммы последовательностей (UML)
- [ ] Поведение
  - [ ] Взаимодействия (Table)
  - [ ] Механизмы безопасности
  - [ ] Прочие поведенческие механизмы
- [ ] Прочие аспекты
- [ ] Сценарии отказа (Table)

#### `deployment` (Диаграммы развёртывания)

- [ ] Типовые варианты развертывания
- [ ] Вариант развертывания
- [ ] При наличии отдельных элементов развертывания (сайдкар (sidecar), агент и пр.)

#### `agent-guide` (Руководство прикладного администратора)

- [ ] Общие сведения (АС Документация Сотрудники)
- [ ] agent.json
- [ ] Установка
- [ ] Порядок установки
- [ ] Обновление
- [ ] Удаление
- [ ] Часто встречающиеся проблемы и пути их устранения

#### `release-notes` (Примечания к релизу)

- [ ] Секция версии продукта
- [ ] Компонентный состав (АС Документация Сотрудники)
- [ ] Изменение функциональности (АС Документация Сотрудники)
- [ ] Исправленные ошибки (АС Документация Сотрудники)
- [ ] Устраненные уязвимости (АС Документация Сотрудники)
- [ ] Обратная совместимость (рукописный)
- [ ] Известные проблемы (рукописный)
- [ ] Изменения в параметрах установки и настройки (рукописный)
- [ ] Изменения в документации (рукописный)

#### `test-plan` / `pmi` (Программа и методика испытаний)

- [ ] Объект испытаний и требования (АС Документация Сотрудники)
- [ ] Методы испытаний (АС Документация Сотрудники)
- [ ] Изменение функциональности (АС Документация Сотрудники)
- [ ] Исправленные ошибки (АС Документация Сотрудники)
- [ ] Регрессионные тесты (АС Документация Сотрудники)
- [ ] Регрессионные тесты должны совпадать с Основными функциями документа Описание

### 3. Reference Integrity

Verify that:

- References to other documents are valid
- Links to external resources are accessible
- Cross-references use correct document identifiers
- Section references point to existing sections

### 4. Content Consistency

Check for:

- Terminology consistency across documents
- Version number consistency
- Component name consistency
- API endpoint consistency
- Configuration parameter consistency

### 5. Completeness Checks

Verify:

- All referenced diagrams exist
- All mentioned tables are present
- All appendices are included
- All required signatures/approvals are present

### 6. Document Notes Validation

The following notes from the graph must be validated:

|Note Location       |Content                                                                                                                                                                                 |Validation Rule                                |
|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------|
|`installation-guide`|СПО в Руководстве по установке должно быть отражено на Диаграммах развертывания и в Системных требованиях                                                                               |Cross-reference СПО                            |
|`about`             |В Основных функциях не требуется перечислять все функции продукта, необходимо перечислить только существенные функции. Полный перечень — в разделе «Варианты и сценарии использования»  |Functions are essential-only                   |
|`architecture`      |Компонентно-логическая диаграмма основана на разделах: Компоненты, Варианты и сценарии использования (акторы), Программные интерфейсы, Взаимодействия                                   |Component-logical diagram derived from sections|
|`architecture`      |Диаграммы последовательностей — графическое представление реализации каждого use case (порядок обмена сообщениями, временные зависимости компонентов системы)                           |Sequence diagrams describe each use case       |
|`user-guide`        |При наличии у продукта интерфейсов взаимодействия конечного пользователя (веб-консоль, приложение, утилита командной строки)                                                            |Conditional section                            |
|`developer-guide`   |При наличии у продукта библиотеки (клиентский модуль, фреймворк)                                                                                                                        |Conditional section                            |
|`agent-guide`       |При наличии у продукта отдельных элементов развертывания (сайдкар (sidecar), агент и пр.)                                                                                               |Conditional section                            |
|`security-guide`    |Сведения по ключам и сертификатам должны коррелировать с разделами: Безопасность данных, Сетевая безопасность, Компонентно-логическая диаграмма, Взаимодействия, Диаграммы развертывания|Cross-reference security                       |
|`test-plan`         |Регрессионные тесты должны совпадать с Основными функциями документа Описание                                                                                                           |Check regression tests match functions         |

### 7. Metadata Validation

If `metadata` document exists, verify:

- [ ] dbmodels
- [ ] software-product-integration-cases.json
- [ ] platform-component-integration-cases.json
- [ ] deployment-units.json

Metadata must be consistent with `architecture` document sections.

## Workflow

### ⚠️ CRITICAL CONTEXT CONSTRAINT — Supervisor / Subagent split

This skill runs in a **two-tier** model:

- **Supervisor (main agent)** — reads THIS skill and orchestrates. It finds all files, derives the validation checklist for each file from the skill, and delegates one file at a time to the subagent with a self-contained instruction. It then assembles the final report from `tmp/*.json`. It MUST NEVER read raw `.md` / `.svg` document content.
- **`document-validator-worker` (subagent)** — does NOT have this skill. It receives a complete instruction (file path + required sections + notes + fields to extract), reads that ONE file in its own isolated context, writes `tmp/{doc_type}.json`, and returns only a one-line status.

Raw document content lives ONLY inside a subagent’s isolated context and never reaches the supervisor. All inter-document analysis (Phase 2) is done by the supervisor exclusively through compact `tmp/{doc_type}.json` files.

-----

### Phase 0: Repository Discovery (SUPERVISOR)

**Step 0. Collect file list only — do NOT read file contents yet**

1. Access the repository from the provided URL
1. Navigate to the `documentation` folder in the repository root
1. **If `documentation` folder does not exist — stop and report: no documents folder found**
1. Find all `.md` and `.svg` files recursively inside `documentation/`
1. Build a plain list of file paths — filenames only, no content
   **Use directory listing / glob only (e.g. `find documentation -name '*.md'`). Do NOT open or read any file in this phase.**
1. Write the file list to `tmp/file-list.json`:
   
   ```json
   ["documents/about/index.md", "documents/architecture/index.md", "..."]
   ```
1. Proceed to Phase 1

-----

### Phase 1: Per-File Delegation Loop (SUPERVISOR)

**🚫 ABSOLUTE RULE — the supervisor (main agent) NEVER reads source documents.**

The supervisor must NOT call `read_file` on any `.md` / `.svg` document.
The supervisor’s job is to read THIS skill, and for each file derive a concrete validation instruction, then hand it to the `document-validator-worker` subagent. Only the subagent reads the file content (in its own isolated context).

**For each file, the supervisor prepares the instruction WITHOUT opening the file:**

1. Determine `doc_type` from the file path / folder name
   (e.g. `documents/about/index.md` → `about`, `documents/architecture/...` → `architecture`).
1. From this skill, look up for that `doc_type`:
- the full list of **required sections** (section “2. Required Sections Validation”)
- the **per-document notes** to validate (section “6. Document Notes Validation”)
- which fields to extract (`components`, `spo_list`, `key_terms`, `version`, `cross_refs`)
1. Build an explicit instruction string containing all of the above — the subagent does NOT have this skill, so everything it needs must be in the instruction.

**Mandatory delegation cycle (repeat for EVERY file in `tmp/file-list.json`, in order):**

```
┌────────────────────────────────────────────────────────────────┐
│ SUPERVISOR loop — FOR file[i] in tmp/file-list.json:             │
│                                                                  │
│   1. doc_type = type derived from file path                      │
│   2. instruction = required sections + notes + fields to extract │
│                    for this doc_type (taken from THIS skill)     │
│   3. task(                                                       │
│        subagent="document-validator-worker",                     │
│        description=instruction  ← full self-contained checklist  │
│      )                                                           │
│   4. receive ONLY a one-line status from the subagent            │
│      e.g. "DONE about: 3 issues, saved tmp/about.json"           │
│   5. go to file[i+1]                                             │
│                                                                  │
│ The supervisor NEVER reads file content. It only reads the skill │
│ and forwards instructions. The subagent does the actual reading. │
└────────────────────────────────────────────────────────────────┘
```

**Instruction template the supervisor sends in `task` (fill in per file):**

```
Validate ONE documentation file and write the result to tmp/{doc_type}.json.

file_path: documents/about/index.md
doc_type: about

Required sections to check (mark each present/missing):
- Назначение
- Преимущества
- Системные требования
- Основные функции
- Варианты и сценарии использования
- ... (full list for this doc_type from the skill)

Notes to validate:
- В Основных функциях перечислять только существенные функции; полный перечень — в разделе «Варианты и сценарии использования».

Extract these fields: sections_found, sections_missing, components,
spo_list, key_terms, version, cross_refs.

Then write tmp/{doc_type}.json in this exact format: { ...schema... }
Return ONLY: "DONE {doc_type}: {n} issues, saved tmp/{doc_type}.json".
Do NOT return file content.
```

**What the SUBAGENT (`document-validator-worker`) does — for ONE file only:**

The subagent has NO access to this skill. It works strictly from the instruction it receives:

1. Read the file at `file_path` (in its own isolated context).
1. Apply the checklist from the instruction: check each required section, validate the listed notes, extract the listed fields, collect per-file issues.
1. Write the compact analysis to `tmp/{doc_type}.json` using `write_file`.
   **Strictly inside `tmp/` — no subdirectories, no prefixes.**
   Example paths: `tmp/about.json`, `tmp/architecture.json`, `tmp/installation-guide.json`
1. Return to the supervisor ONLY a one-line status:
   `DONE {doc_type}: {n} issues, saved tmp/{doc_type}.json`
   **Never return raw file content to the supervisor.**

**`tmp/{doc_type}.json` format produced by the subagent:**

```json
{
  "file": "documents/about/index.md",
  "doc_type": "about",
  "sections_found": ["Назначение", "Преимущества", "Основные функции"],
  "sections_missing": ["Системные требования", "Нефункциональные особенности"],
  "components": ["ServiceA", "ServiceB"],
  "spo_list": ["PostgreSQL 14", "Redis 6.2", "Nginx 1.24"],
  "key_terms": ["термин1", "термин2"],
  "version": "2.1.0",
  "cross_refs": ["installation-guide", "architecture"],
  "issues": [
    {
      "code": "CVAL",
      "path": "documents/about/",
      "severity": "ERROR",
      "message": "Отсутствует обязательный раздел 'Системные требования'",
      "position": null,
      "advice": "Добавить раздел с аппаратными и программными требованиями"
    }
  ]
}
```

**End of Phase 1:** every file in `tmp/file-list.json` has a matching `tmp/{doc_type}.json`,
and the supervisor context contains only the short status lines — no document content.

-----

### Phase 2: Cross-Document Consistency (SUPERVISOR)

**⚠️ Read ONLY `tmp/*.json` files in this phase. Never re-read original documents.**

**Step 5. Load all compact analyses**

Read all `tmp/*.json` files except `tmp/file-list.json`. These are small and safe for context.

**Step 6. Run graph-based consistency checks**

Using only the extracted fields (`spo_list`, `components`, `key_terms`, `sections_found`, `version`), validate all consistency links:

|Link Type                |Documents                                                   |Fields to Compare                                                     |
|-------------------------|------------------------------------------------------------|----------------------------------------------------------------------|
|СПО (red)                |`about` ⟷ `installation-guide` ⟷ `release-notes`            |`spo_list` must match across all three                                |
|Логическая (blue)        |`about` ⟷ `user-guide` ⟷ `administration-guide`             |Use-case scenario names in `key_terms`                                |
|Логическая (blue)        |`installation-guide` ⟷ `administration-guide` ⟷ `user-guide`|Configuration parameter names in `key_terms`                          |
|Логическая (blue)        |`about` ⟷ `release-notes` ⟷ `test-plan`                     |Product function names in `key_terms`                                 |
|Логическая (blue)        |`architecture` ⟷ `deployment` ⟷ `installation-guide`        |`components` must be consistent                                       |
|Логическая (blue)        |`security-guide` ⟷ `administration-guide` ⟷ `user-guide`    |Security setting names in `key_terms`                                 |
|Логическая (blue)        |`administration-guide` ⟷ `about`                            |Admin scenario names in `key_terms`                                   |
|Логическая (blue)        |`developer-guide` ⟷ `agent-guide`                           |General info consistency in `sections_found`                          |
|Логическая (blue)        |`release-notes` ⟷ `test-plan`                               |Fixed bug identifiers in `key_terms`                                  |
|Включение (green)        |`architecture` → `metadata`                                 |`components` in architecture must appear in metadata JSON files       |
|Ссылка (orange)          |`architecture` → `deployment`                               |`cross_refs` in architecture must include deployment                  |
|Зависимость (blue dotted)|`user-guide`, `developer-guide`, `agent-guide`, `deployment`|Presence depends on component composition — check against `components`|

**Step 7. Validate document notes**

Using extracted fields only, check all notes from the graph:

- СПО note in `installation-guide`: `spo_list` reflected in `deployment` components
- Functions note in `about`: `sections_found` contains both “Основные функции” and “Варианты и сценарии использования”
- Component-logical diagram note in `architecture`: `sections_found` contains all four source sections
- Sequence diagrams note in `architecture`: `sections_found` contains “Диаграммы последовательностей”
- Conditional sections: flag as WARNING if section absent but component composition implies it should exist
- Keys/certificates note in `security-guide`: relevant section names present in `sections_found`
- Regression tests note in `test-plan`: regression test names overlap with function names from `about`

**Step 8. Generate final report**

Merge all `issues` arrays from `tmp/*.json` with cross-document issues from Steps 6–7.

Save to `{workspace_path}/reports/consistency-validator.json`.

**Step 9. Cleanup**

Delete all files inside `tmp/` — both `tmp/file-list.json` and all `tmp/{doc_type}.json` files.

-----

## Output Format

The validation result must be saved as a JSON file named `consistency-validator.json` in the workspace directory.

### JSON Structure

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

### Report Fields

|Field     |Type   |Description                                           |
|----------|-------|------------------------------------------------------|
|`title`   |string |Report title (default: “Согласованность документации”)|
|`priority`|integer|Priority level (default: 15)                          |
|`issues`  |array  |List of validation issues                             |

### Issue Fields

|Field     |Type       |Required|Description                                                                                       |
|----------|-----------|--------|--------------------------------------------------------------------------------------------------|
|`code`    |string     |Yes     |Issue code (default: “CVAL”)                                                                      |
|`path`    |string     |Yes     |Path to file/directory with the issue. Must always start with `documents/`, never `documentation/`|
|`severity`|enum       |Yes     |One of: `ERROR`, `WARNING`, `INFO`, `SUGGESTION`                                                  |
|`message` |string     |Yes     |Issue description                                                                                 |
|`position`|string|null|No      |Position in source (line number, range)                                                           |
|`advice`  |string|null|No      |Recommendation for fixing the issue                                                               |

### Severity Levels

|Level       |Description                                     |
|------------|------------------------------------------------|
|`ERROR`     |Significant content mismatches                  |
|`WARNING`   |Conditional sections missing, terminology issues|
|`INFO`      |Style notes, minor suggestions                  |
|`SUGGESTION`|Improvement recommendations                     |

### File Output

The agent must save the JSON report to:

```
{workspace_path}/reports/consistency-validator.json
```

Where `workspace_path` is `/docstorage/tmp/{{workflow.uid}}/` in the Argo Workflows context.

## Final Output Message

After saving `consistency-validator.json`, the agent **must** print a summary message in the following exact format. No deviations.

```
Валидация завершена.

Результаты по категориям:
  • Ошибки (ERROR):       {error_count}
  • Предупреждения (WARNING): {warning_count}
  • Информация (INFO):    {info_count}
  • Рекомендации (SUGGESTION): {suggestion_count}
  ─────────────────────────
  Всего issues:           {total_count}

Проверено документов: {docs_checked} из {docs_total}
Статус: {PASSED|FAILED}

Полный отчёт сохранён:
  /docstorage/tmp/{workflow.uid}/reports/consistency-validator.json
```

### Rules for the message

- `{error_count}` — count of issues where `severity == "ERROR"`
- `{warning_count}` — count of issues where `severity == "WARNING"`
- `{info_count}` — count of issues where `severity == "INFO"`
- `{suggestion_count}` — count of issues where `severity == "SUGGESTION"`
- `{total_count}` — sum of all four counts
- `{docs_checked}` — number of `tmp/{doc_type}.json` files successfully written
- `{docs_total}` — total number of files in `tmp/file-list.json`
- `{PASSED|FAILED}` — `PASSED` if `error_count == 0`, otherwise `FAILED`
- `{workflow.uid}` — real UID from the Argo Workflows context, not the placeholder text

### Example

```
Валидация завершена.

Результаты по категориям:
  • Ошибки (ERROR):            5
  • Предупреждения (WARNING):  3
  • Информация (INFO):         1
  • Рекомендации (SUGGESTION): 2
  ─────────────────────────────
  Всего issues:                11

Проверено документов: 8 из 8
Статус: FAILED

Полный отчёт сохранён:
  /docstorage/tmp/abc-123-def-456/reports/consistency-validator.json
```

-----

## Rules

1. **Be thorough**: Check all applicable rules for the document type
1. **Be specific**: Point to exact sections and line numbers when possible
1. **Be actionable**: Provide clear recommendations for each issue
1. **Prioritize**: Mark issues as Error, Warning, or Info
1. **Stay objective**: Base findings on actual content, not assumptions
1. **One file at a time**: Never hold more than one source document in context simultaneously

## Critical Requirements

|Requirement  |Specification                                         |
|-------------|------------------------------------------------------|
|Completeness |Check all mandatory sections for document type        |
|Accuracy     |Verify claims against actual document content         |
|Consistency  |Compare across all related documents                  |
|Actionability|Provide fix recommendations for each issue            |
|Language     |Output in Russian, preserve technical terms in English|
|Context      |Process one file at a time; use tmp JSON for Phase 2  |

## Constraints

1. Do not validate content outside the documentation scope
1. Do not make assumptions about missing documents
1. Do not skip sections that appear optional but are required
1. Save results as JSON file `consistency-validator.json` in workspace
1. **Never re-read raw document files during Phase 2** — use only `tmp/{doc_type}.json`

## Examples

### Example 1: Missing Section

```
❌ Проблема: В документе "Руководство администратора" отсутствует обязательный раздел "Мониторинг"

Рекомендация: Добавить раздел с описанием:
- Метрик для мониторинга
- Инструментов мониторинга
- Пороговых значений для алертов
```

### Example 2: SPO Inconsistency

```
❌ Проблема: Список СПО в "Руководстве по установке" не совпадает с "Описанием"

installation-guide spo_list: ["PostgreSQL 14", "Redis 6.2", "Nginx 1.24"]
about spo_list:               ["PostgreSQL 13", "Redis 6.2"]

Несоответствия:
- PostgreSQL: версия 14 vs 13
- Nginx 1.24: присутствует только в installation-guide

Рекомендация: Привести версии PostgreSQL к единому значению во всех документах.
Добавить Nginx в раздел "Системные требования" документа "Описание".
```

### Example 3: Cross-reference integrity

```
❌ Проблема: Компонент "AuthService" упомянут в architecture, но отсутствует в deployment

architecture components: ["AuthService", "ApiGateway", "UserService"]
deployment components:   ["ApiGateway", "UserService"]

Рекомендация: Добавить элемент развертывания для "AuthService" в диаграммы развертывания.
```