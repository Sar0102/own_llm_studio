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

### Phase 0: Repository Discovery

**Step 0. Find all markdown files in documentation folder**

When user provides a repository URL:

1. Clone or access the repository from the provided URL
1. Navigate to the `documentation` folder in the repository root
1. **If `documentation` folder does not exist — stop validation and report that no documents folder found**
1. Find all `.md` or `.svg` files recursively inside `documents/` folder:
- Use `find documents -name '*.md'` or equivalent
1. Build a list of all markdown files to validate
1. Read the content of each `.md` file
1. Proceed to Phase 1 with the collected documents

### Phase 1: Document Analysis

**Step 1. Identify document types**

Analyze the provided document(s) and identify:

- Document type from the table above
- Document sections present
- References to other documents

**Step 2. Extract key information**

For each document, extract:

- Document metadata (version, date, author)
- Section list with hierarchy
- Cross-references (internal and external)
- Tables and figures list
- Terminology used

**Step 3. Build dependency graph**

Create a map of:

- Which documents reference which
- Which sections depend on other sections
- External dependencies (tools, systems, APIs)

### Phase 2: Validation

**Step 4. Check required sections**

For each document type, verify all mandatory sections exist according to the graph.

**Step 5. Validate cross-references**

Check that:

- Internal references point to existing sections
- External document references are valid
- No circular dependencies exist
- References to “АС Документация Сотрудники” are valid
- References to UML diagrams, Tables, JSON files are valid

**Step 6. Content consistency check (Graph-based)**

Validate all consistency links from the graph:

|Link Type                |Documents                                                   |What to Check                                                          |
|-------------------------|------------------------------------------------------------|-----------------------------------------------------------------------|
|СПО (red)                |`about` ⟷ `installation-guide` ⟷ `release-notes`            |Перечень СПО / Системные требования должны совпадать                   |
|Логическая (blue)        |`about` ⟷ `user-guide` ⟷ `administration-guide`             |Консистентность сценариев использования                                |
|Логическая (blue)        |`installation-guide` ⟷ `administration-guide` ⟷ `user-guide`|Консистентность параметров настройки                                   |
|Логическая (blue)        |`about` ⟷ `release-notes` ⟷ `test-plan`                     |Консистентность функций продукта                                       |
|Логическая (blue)        |`architecture` ⟷ `deployment` ⟷ `installation-guide`        |Консистентность компонентов                                            |
|Логическая (blue)        |`security-guide` ⟷ `administration-guide` ⟷ `user-guide`    |Консистентность настроек безопасности                                  |
|Логическая (blue)        |`administration-guide` ⟷ `about`                            |Консистентность сценариев администрирования                            |
|Логическая (blue)        |`developer-guide` ⟷ `agent-guide`                           |Консистентность общих сведений                                         |
|Логическая (blue)        |`release-notes` ⟷ `test-plan`                               |Консистентность исправленных ошибок                                    |
|Включение (green)        |`architecture` → `metadata`                                 |Включение метаданных (dbmodels, *.json)                                |
|Ссылка (orange)          |`architecture` → `deployment`                               |Диаграммы развертывания подключаются ссылкой                           |
|Зависимость (blue dotted)|`user-guide`, `developer-guide`, `agent-guide`, `deployment`|Наличие документа зависит от компонентного состава (условные документы)|

**Step 7. Validate document notes**

Check all notes from the graph are properly handled:

- СПО note in `installation-guide`
- Functions note in `about`
- Component-logical diagram note in `architecture`
- Sequence diagrams note in `architecture`
- Conditional sections in `user-guide`, `developer-guide`, `agent-guide`, `deployment`
- Keys/certificates correlation note in `security-guide`
- Regression tests note in `test-plan`

**Step 8. Generate validation report**

Create a report with:

- List of missing sections
- List of broken references
- List of inconsistencies (by link type)
- List of note violations
- Recommendations for fixes

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

### Issue (Statement) Fields

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

### JSON Examples

<!-- TODO(Sarvar): сюда вставь оригинальное содержимое блока "### JSON Examples"
     (примерно строки 417–466 исходного файла) — этот фрагмент не попал на скриншоты,
     поэтому я его не реконструировал, чтобы не подменить твои реальные примеры. -->

## Rules

1. **Be thorough**: Check all applicable rules for the document type
1. **Be specific**: Point to exact sections and line numbers when possible
1. **Be actionable**: Provide clear recommendations for each issue
1. **Prioritize**: Mark issues as Error, Warning, or Info
1. **Stay objective**: Base findings on actual content, not assumptions

## Critical Requirements

|Requirement  |Specification                                         |
|-------------|------------------------------------------------------|
|Completeness |Check all mandatory sections for document type        |
|Accuracy     |Verify claims against actual document content         |
|Consistency  |Compare across all related documents                  |
|Actionability|Provide fix recommendations for each issue            |
|Language     |Output in Russian, preserve technical terms in English|

## Constraints

1. Do not validate content outside the documentation scope
1. Do not make assumptions about missing documents
1. Do not skip sections that appear optional but are required
1. Save results as JSON file `consistency-validator.json` in workspace

## Examples

### Example 1: Missing Section

```
❌ Проблема: В документе "Руководство администратора" отсутствует обязательный раздел "Мониторинг"

Рекомендация: Добавить раздел с описанием:
- Метрик для мониторинга
- Инструментов мониторинга
- Пороговых значений для алертов
```

<!-- TODO(Sarvar): если в исходнике после строки 506 были Example 2, Example 3 и т.д. —
     добавь их сюда; конец файла не попал на скриншоты. -->