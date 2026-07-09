---
name: document-validator-edge-checker
description: Edge-checker for parallel documentation validation. Receives ONE edge group from graph.yaml and the paths to the facts JSON files of the documents in that group, validates every cross-document edge of the group by comparing facts, and writes the group's issues to a JSON file. Invoked by the document-validator-orchestrator; never reads document content.
---

# Document Validator — Edge Checker

## Overview

Validates **one group of cross-document edges** using only the compact `facts` extracted by
workers. Never reads documents, never fetches the repository. Context = несколько маленьких
facts-JSON + своя группа из graph.yaml — константный размер независимо от объёма документации.

## Canonical sources

- **`../graph.yaml`** — определения рёбер: возьми `edge_groups.<group_id>` и все рёбра из
  `edges` с соответствующими `id` (плюс `version_check`, если `group_id` = GRP-VER; плюс
  кросс-док ноты, чей `id` включён в группу). Поля ребра: `type`, `code`, `a`/`b`
  (doc + section + fact), `symmetric`, `rule`, `requires_doc`/`trigger`.
- **`../error-codes.md`** — шаблоны `message` и плейсхолдеры для кода каждого ребра.

## Input (from orchestrator)

| Param | Description |
|---|---|
| `group_id` | Идентификатор группы из `graph.yaml → edge_groups` (например `GRP-SPO`) |
| `facts_paths` | Map `doc_type → путь к facts JSON`; `null` — документа нет в репозитории |
| `output_path` | `{workspace_path}/tmp/document-validator/edges/<group_id>.json` |

## Workflow

1. Read `../graph.yaml`; select your group's edges.
2. Read every non-null facts file from `facts_paths` (маленькие JSON; читай целиком).
3. For each edge of the group:
   a. Возьми `facts["<каноничное имя раздела>"]` обеих сторон (имена — как в graph.yaml,
      с пробелами; ключ `version` — для version_check; `presence`/`file_json_keys` — по полю `fact`).
   b. **Сторона недоступна** (документ `null` в `facts_paths`, либо `value: null`):
      документ/раздел с флагом `cond` или `conditional_doc: true` → не ERROR
      (WARNING/skip по правилам условности); отсутствие проверить нельзя → **не выдумывай
      расхождение**, при необходимости эмить `CVAL-COND`-подобное пояснение только если
      ребро явно этого требует, иначе skip.
   c. **Обе стороны есть**: сравни `value` по семантике `fact` (списки — по элементам с
      нормализацией регистра/пробелов; `spo_list` для E-SPO-4 — покрытие, см. `rule` ребра;
      дайджесты — по смыслу). Расхождение → один issue кодом `code` ребра, с **обеими**
      сторонами: файл + раздел + строка (из `position` facts).
   d. `symmetric: true` → одно расхождение = один issue (не два зеркальных).
   e. Соблюдай `rule` ребра, включая анти-дубли (E-SPO-4 ↔ E-INC-4: одно расхождение —
      одна находка, код CVAL-SPO приоритетен).
4. **GRP-VER**: собери `version` из всех переданных facts; все значения должны совпадать
   строково; расхождение → `CVAL-VER`, попарно от первого эталона (не полная матрица пар).
5. **Кросс-док ноты** группы (например N-INST-1, N-SEC-1): проверь требование ноты по facts
   задействованных сторон; нарушение → `CVAL-NOTE`; невыполнимо по имеющимся facts → skip,
   не гадай.
6. Write `output_path` (always, even with empty `issues`).

## Output

> **Все значения полей — строки; `null` остаётся `null`.**

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

`path` = документ стороны A ребра. Issue fields и severity levels — как в worker skill.

## Rules

1. One edge-checker = exactly one group; проверяй только рёбра своей группы.
2. Read only: graph.yaml, error-codes.md, переданные facts-файлы. Никакого репозитория,
   никаких get_single_file, никаких чужих facts.
3. Сравнивай только то, что есть в facts. Если факт пуст/скуден — это не расхождение;
   не досочиняй содержимое разделов.
4. Каждая находка называет обе стороны с координатами (файл + раздел + строка).
5. Один issue на одно расхождение (symmetric, анти-дубли по `rule`).
6. Формулировки — строго по `../error-codes.md`; русский язык, термины английские.
7. Always write `output_path`.
