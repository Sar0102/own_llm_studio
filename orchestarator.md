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

## Source Graph (canonical — single source of truth)

Validation MUST follow this graph. It is authoritative for document types, required sections (with
nesting and `Table`/`UML`/`ссылка`/`рукописный` markers), notes, and **every** consistency edge.
If anything in this skill ever disagrees with the graph below, the graph wins. Intra-document edges
(both endpoints in the same document) are validated by the **worker**; cross-document edges (Phase 3)
by the orchestrator.

```plantuml
@startuml
left to right direction
skinparam Shadowing false

legend
Легенда:
==== color:red --- color:black : Перечень СПО должен совпадать
==== color:blue --- color:black : Логические связи и консистентность контента
==== color:green --- color:black : Включение части контента одного раздела в другой
==== color:orange --- color:black : Контент в виде ссылки
==== color:blue --> color:black : Наличие документов и разделов зависит от компонентного состава
end legend

object "Описание" as about << document >> {
  Назначение / Преимущества / Системные_требования
  ___Необходимое_программное_обеспечение (АС Документация Сотрудники) / ___Аппаратное_обеспечение (Table)
  Типовые_решения / ___Типовое_решение
  Концептуальная_модель_предметной_области (UML) / Основные_функции (Table)
  Варианты_и_сценарии_использования (UML) / ___Сценарий_использования / ___Сценарий_использования_n
  Нефункциональные_особенности / Совместимость_с_выпущенными_клиентами
}
object "Детальная архитектура" as ar1 << document >> {
  Структура
  ___Компонентно_логическая_диаграмма (UML) / ___Компоненты (Table) / ___Программные_интерфейсы
  ___Схемы_структур_данных / ___Физические_модели_баз_данных / ___Элементы_развертывания (Table)
  ___Диаграммы_развертывания (ссылка)
  Поведение / ___Взаимодействия (Table) / ___Диаграммы_последовательностей (UML)
  ___Механизмы_безопасности / ___Прочие_поведенческие_механизмы
  Прочие_аспекты / ___Сценарии_отказа (Table)
}
object "Диаграммы развертывания" as dd << document >> { Типовые_варианты_развертывания / ___Вариант_развертывания }
object "Руководство по установке <installation-guide>" as inst << document >> {
  Подготовка_окружения / ___Подготовка_элементов_развертывания / ___Настройка_окружения / ___Выпуск_и_подготовка_сертификатов
  Установка / ___Порядок_установки / ___Настройка_интеграции
  Чек_лист_проверки_корректности_работы
  Обновление / ___Изменения_в_системных_требованиях / ___Изменения_в_параметрах_настройки
  Откат / Удаление / Часто_встречающиеся_проблемы_и_пути_их_устранения
}
object "Руководство администратора <administration-guide>" as admin << document >> {
  Сценарии_администрирования / ___Как_определить_версию_продукта / ___Сценарий_администрирования
  Системный_журнал / ___Настройка_системного_журнала / ___Доступ_к_системному_журналу / ___Основные_события
  Мониторинг / ___Настройка / ___Метрики (Table)
  Часто_встречающиеся_проблемы_и_пути_их_устранения
}
object "Руководство прикладного администратора <agent-guide>" as agent << document >> {
  Общие_сведения (АС Документация Сотрудники) / agent.json
  Установка / ___Порядок_установки / Обновление / Удаление / Часто_встречающиеся_проблемы_и_пути_их_устранения
}
object "Руководство пользователя <user-guide>" as user << document >> {
  Доступ_к_приложению / ___Запуск_приложения / ___Вход_и_выход / ___Порядок_доступа / ___Роли_пользователей (Рукописный)
  Использование_приложения / ___Сценарий_использования / ___Как_определить_версию_продукта
  Настройка_приложения / Часто_встречающиеся_проблемы_и_пути_их_устранения
}
object "Руководство прикладного разработчика <developer-guide>" as dev << document >> {
  Общие_сведения (АС Документация Сотрудники) / lib.json
  Подключение_и_конфигурирование / Миграция_на_текущую_версию / Быстрый_старт (ссылка на example.zip)
  Использование / ___Сценарий_использования / Часто_встречающиеся_проблемы_и_пути_их_устранения
}
object "Руководство по безопасности <security-guide>" as secure << document >> {
  Идентификация_и_аутентификация / Авторизация / Безопасность_данных / Сетевая_безопасность
  Управление_ключами_и_сертификатами (Table) / Аудит (Table)
  Правила_эксплуатации / Настройки_параметров_безопасности / Чек-лист_валидации_настройки_механизмов_безопасности
}
object "Программа и методика испытаний <pmi>" as pmi << document >> {
  Объект_испытаний_и_требования (АС Документация Сотрудники) / Методы_испытаний (АС Документация Сотрудники)
  ___Изменение_функциональности / ___Исправленные_ошибки / ___Регрессионные_тесты
}
object "Примечания к релизу <release-notes>" as rn << document >> {
  Секция_версии_продукта / ___Компонентный_состав / ___Изменение_функциональности / ___Исправленные_ошибки / ___Устраненные_уязвимости
  ___Обратная_совместимость (рукописный) / ___Известные_проблемы (рукописный) / ___Изменения_в_параметрах_установки_и_настройки (рукописный) / ___Изменения_в_документации (рукописный)
}
object "Метаданные <info>" as info << info >> { db-models.json / deployment-units.json }

' === Notes ===
' about: в Основных функциях перечисляются только сущностные функции; полный перечень — в «Варианты и сценарии использования»
' ar1: компонентно-логическая диаграмма основана на Компоненты/Варианты и сценарии(акторы)/Программные интерфейсы/Взаимодействия
' ar1: диаграммы последовательностей = графическое представление каждого use case
' inst: СПО в Руководстве по установке отражается на Диаграммах развертывания и в Системных требованиях
' agent: при наличии отдельных элементов развертывания (sidecar, агент)
' user: при наличии интерфейса взаимодействия конечного пользователя (веб-консоль, приложение, CLI)
' dev: при наличии библиотеки (клиентский модуль, фреймворк)
' secure: сведения по ключам/сертификатам коррелируют с Безопасность данных/Сетевая безопасность/Компонентно-логическая диаграмма/Взаимодействия/Диаграммы развертывания

' === Edges (Зависимость, blue dashed) ===
agent -[#blue,dashed]-> about::Совместимость_с_выпущенными_клиентами
ar1::___Элементы_развертывания -[#blue,dashed]-> agent
ar1::___Программные_интерфейсы -[#blue,dashed]-> user

' === Edges (СПО, red) ===
about::Системные_требования -[#red]-> inst::Чек_лист_проверки_корректности_работы
about::Системные_требования -[#red]-> dd::___Вариант_развертывания
about::Системные_требования -[#red]-> secure::Настройки_параметров_безопасности
about::Системные_требования -[#red]-> ar1::___Сценарии_отказа

' === Edges (Включение, green) ===
ar1::___Программные_интерфейсы -[#green]-> ar1::___Компоненты
ar1::___Сценарии_отказа -[#green]-> ar1::___Компоненты
ar1::___Сценарии_отказа -[#green]-> about::___Необходимое_программное_обеспечение
ar1::___Диаграммы_последовательностей -[#green]-> ar1::___Компоненты

' === Edges (Ссылка, orange) ===
ar1::___Диаграммы_развертывания -[#orange]-> dd : ссылка на Диаграммы развертывания

' === Edges (Логическая, blue) ===
dd::___Вариант_развертывания -[#blue]-> info::deployment-units.json
ar1::___Физические_модели_баз_данных -[#blue]-> info::db-models.json
ar1::___Механизмы_безопасности -[#blue]-> secure : консистентность с документом РБ
dd::___Вариант_развертывания -[#blue]-> ar1::___Элементы_развертывания
dd::___Вариант_развертывания -[#blue]-> ar1::___Взаимодействия
about::Варианты_и_сценарии_использования -[#blue]-> ar1::___Диаграммы_последовательностей
about::Нефункциональные_особенности -[#blue]-> ar1::___Механизмы_безопасности
admin::Сценарии_администрирования -[#blue]-> about::___Сценарий_использования : консистентность сценариев
user::Использование_приложения -[#blue]-> about::___Сценарий_использования_n : консистентность сценариев
secure::Авторизация -[#blue]-> admin::___Сценарий_администрирования
rn::___Изменение_функциональности <-[#blue]-> pmi::___Изменение_функциональности
rn::___Исправленные_ошибки <-[#blue]-> pmi::___Исправленные_ошибки
rn::___Устраненные_уязвимости <-[#blue]-> pmi::___Исправленные_ошибки
inst::Обновление -[#blue]-> rn::___Изменения_в_параметрах_установки_и_настройки
dd -[#blue]-> secure::Настройки_параметров_безопасности
@enduml
```

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

1. Use the remote repository integration (source-control tool) for the provided URL — **do not clone locally**.
2. Enumerate every `.md` file under `documentation/documents` via the repository listing/source-control tool (remote — e.g. a repo-tree / list-files call). If that path does not exist — stop and report that no documents folder found.
3. Each file = one unit of work for one worker. The orchestrator does **not** read file content here — workers fetch it via `get_single_file`.
4. Create `{workspace_path}/tmp/document-validator/`.

### Phase 1: Parallel Dispatch (one worker per file)

For each file, spawn a `document-validator-worker` subagent and pass:
- `file_path` — **repository-relative** path to the file (remote; the worker reads it via `get_single_file`).
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

Use the per-file `facts` to validate **only the cross-document edges** of the graph (endpoints in
different documents). Intra-document edges (e.g. `architecture::Сценарии_отказа → architecture::Компоненты`)
are checked by the worker. Facts are **section-keyed**: `facts["<Раздел>"] = { value, section, position }`.
For each edge compare the `value` of the two endpoint sections; on mismatch emit an issue naming
**both** sides (file + section + line). A side whose section is absent (`value: null`) is reported per
the severity rules (conditional → not ERROR).

**Зависимость (blue dashed) — наличие документа зависит от компонентного состава:**
| Architecture content present | Required doc | Rule |
|---|---|---|
| `architecture::Элементы_развертывания` | `agent-guide` | есть элементы развертывания (sidecar/агент) → `agent-guide` должен существовать; иначе опционален |
| `architecture::Программные_интерфейсы` | `user-guide` | есть интерфейсы взаимодействия → `user-guide` должен существовать; иначе опционален |
| `agent-guide` существует | `about::Совместимость_с_выпущенными_клиентами` | наличие согласуется с разделом совместимости |

Отсутствие опционального документа → не ERROR.

**СПО (red) — `about::Системные_требования` должен совпадать / быть отражён в:**
- `installation-guide::Чек_лист_проверки_корректности_работы`
- `deployment::Вариант_развертывания`
- `security-guide::Настройки_параметров_безопасности`
- `architecture::Сценарии_отказа`

**Включение (green, кросс-документное):**
- `architecture::Сценарии_отказа` включает `about::Необходимое_программное_обеспечение`

**Ссылка (orange):**
- `architecture::Диаграммы_развертывания` → ссылка должна вести в существующий документ `deployment`

**Логическая (blue) — попарная консистентность разделов:**
| A | B |
|---|---|
| `deployment::Вариант_развертывания` | `metadata::deployment-units.json` |
| `architecture::Физические_модели_баз_данных` | `metadata::db-models.json` |
| `architecture::Механизмы_безопасности` | `security-guide` (документ РБ) |
| `deployment::Вариант_развертывания` | `architecture::Элементы_развертывания` |
| `deployment::Вариант_развертывания` | `architecture::Взаимодействия` |
| `about::Варианты_и_сценарии_использования` | `architecture::Диаграммы_последовательностей` |
| `about::Нефункциональные_особенности` | `architecture::Механизмы_безопасности` |
| `administration-guide::Сценарии_администрирования` | `about::Сценарий_использования` |
| `user-guide::Использование_приложения` | `about::Сценарий_использования_n` |
| `security-guide::Авторизация` | `administration-guide::Сценарий_администрирования` |
| `release-notes::Изменение_функциональности` | `pmi::Изменение_функциональности` |
| `release-notes::Исправленные_ошибки` | `pmi::Исправленные_ошибки` |
| `release-notes::Устраненные_уязвимости` | `pmi::Исправленные_ошибки` |
| `installation-guide::Обновление` | `release-notes::Изменения_в_параметрах_установки_и_настройки` |
| `deployment` (документ) | `security-guide::Настройки_параметров_безопасности` |

**Version consistency** (cross-cutting, не ребро графа): collect the `version` fact from every
document that declares it and compare values; on divergence emit one issue naming each side's
file + section + line (e.g. `D-6.0.0` vs `6.0.0`).

The orchestrator never inspects intra-document section trees — that is the worker's job. Apply the
same severity/conditionality rules as the worker (conditional → not ERROR; version-aware → SUGGESTION).
There is **no** regression-tests ↔ «Основные функции» edge in the graph — do not invent it.

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

## Finding Writing Guidance (как ИИ формулирует находки в отчёте)

Rules for the text the agent writes **inside the report** — fields `message` and `advice` of every
issue. Goal: единообразные, точные, действенные формулировки. Язык — **русский; технические термины
и идентификаторы на английском** (`include`, `front-matter`, `deployment-units.json`, имена секций/файлов).

`message` (что не так):
- Одно-два предложения, по факту: **что** не так и **где** (документ, раздел, строка из `section`/`position`). Пример: «Раздел "Метрики (Table)" отсутствует в `administration-guide` (раздел Мониторинг, L80)».
- Без модальности и эмоций: «отсутствует», «не совпадает», «ссылка не разрешается» — не «кажется», «возможно», «к сожалению».
- Конкретика вместо общего: приводи имя секции/файла/связи, а не «есть проблема со структурой».
- Для кросс-документных находок указывай **обе** стороны с координатами: «'D-6.0.0' (`installation-guide`, Версия, L4) ≠ '6.0.0' (`release-notes`, Версия, L2)».
- Не дублируй значение секрета/чувствительных данных; не цитируй большие фрагменты — ссылайся на место.
- Термины и идентификаторы — в backticks; русские названия разделов — как в графе.

`advice` (что сделать):
- Императив, одно действие: «Добавить раздел "Метрики (Table)" в Мониторинг», «Привести версию к формату `6.0.0`», «Заменить `ЕФС` на «фронтенд»».
- Действенно и проверяемо; без общих советов «улучшить документацию».
- Если правка не очевидна или зависит от продукта — `advice: null`, не выдумывать.

Severity согласована с правилами (worker): реальное отсутствие → `ERROR`; `std_exception_reason`/нота → `INFO`; условный/автогенерируемый раздел → `WARNING`/skip; не было в версии → `SUGGESTION`. Текст находки **не** меняет вердикт — он только описывает его.

Don't:
- ❌ «Похоже, тут что-то не так с разделами» → ✅ «Отсутствует обязательный раздел "Откат" в `installation-guide` (L102)».
- ❌ «Документ неполный» → ✅ «В `about` отсутствует "Варианты и сценарии использования (UML)"; из-за этого нельзя проверить полноту "Основные функции"».
- ❌ хвалебные/извинительные вставки, вопросы к читателю, мета-комментарии о процессе.

### Коды находок

Коды, их значения, severity и шаблоны `message`, а также инструкция по плейсхолдерам **не
дублируются здесь** — они определены в общем файле **`error-codes.md`**, который лежит рядом с этим
SKILL.md в корне скилла `document-validator/` (один общий для orchestrator и worker) и доступен по
пути **`./error-codes.md`**. Перед записью каждой находки (и при сборке отчёта) открой
`./error-codes.md` и возьми оттуда `code`, шаблон `message` и правила подстановки плейсхолдеров.
