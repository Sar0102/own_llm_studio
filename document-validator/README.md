# Document Validator — инструкция по графу

Граф — единственный источник истины о том, **что должно быть в документации** и **что должно
совпадать между документами**. Скиллы не содержат дублирующих чек-листов: правишь граф — меняется
поведение всех субагентов.

## Структура

```
graph/
├── edges.yaml            ← связи МЕЖДУ документами (читают orchestrator и edge-checker)
├── about.yaml            ← дерево разделов одного документа (читает ТОЛЬКО его worker)
├── architecture.yaml
├── administration-guide.yaml
├── ...
└── metadata.yaml
```

Разделение не косметическое: воркер читает **один** файл своего типа (0.5–3 КБ) вместо монолита.
Это то, что удерживает контекст воркера маленьким независимо от размера документации.

| Кто | Что читает |
|---|---|
| worker | `graph/<doc_type>.yaml` — только свой документ |
| edge-checker | `graph/edges.yaml` — только свою группу рёбер |
| orchestrator | `graph/edges.yaml` — рёбра `scope: doc-existence` и `edge_groups` |
| scanner | ничего из графа (работает по `sensitive-data.md`) |

---

## Файл документа — `graph/<doc_type>.yaml`

```yaml
doc_type: administration-guide
title: Руководство администратора
conditional_doc: false        # true → документа может не быть, это не ошибка

sections:                     # дерево разделов; вложенность ТОЛЬКО через children
  - name: Мониторинг
    children:
      - name: Настройка
      - name: Метрики
        markers: [table]

files:                        # артефакты-файлы, НЕ заголовки
  - lib.json

notes:                        # требования, не выражаемые деревом
  - id: N-ADM-1
    scope: intra-doc          # intra-doc → проверяет worker; cross-doc → edge-checker
    text: "..."

facts_to_extract:             # что worker извлекает для сравнения с другими документами
  Сценарии администрирования:
    fact: scenario_names
    spec: Список названий сценариев (только заголовки, без содержимого).
```

### `name` — каноничное имя раздела

Пишется **как реальный заголовок** в `.md`: с пробелами и дефисами, без подчёркиваний.
Это же имя — ключ в `facts` и в рёбрах. Сопоставление с заголовком документа идёт без учёта
регистра, лишних пробелов и завершающей пунктуации.

### `markers` — чем раздел должен быть

| Маркер | Значение | Нарушение |
|---|---|---|
| `table` | ожидается таблица | — |
| `uml` | ожидается блок кода UML | картинка вместо блока → `CVAL-UML-IMG` |
| `ref` | контент подтягивается из внешнего источника (АС Документация) | — |
| `link` | раздел — ссылка на другой документ | — |
| `manual` | рукописный раздел | подключён через `include` → WARNING |

### `flags` — когда отсутствие не ошибка

| Флаг | Значение |
|---|---|
| `cond` | условный раздел — отсутствие даёт WARNING, не ERROR |
| `gen` | автогенерируемый — отсутствие не флагуется вовсе |
| `version_aware` | раздела не было в старых версиях → SUGGESTION |

`conditional_doc: true` на уровне документа — то же самое, но для целого документа
(`agent-guide`, `user-guide`, `developer-guide`: их наличие зависит от состава продукта).

### `files` — это файлы, а не разделы

`lib.json`, `agent.json`, `db-models.json` — артефакты в папке документа. Воркер проверяет их
**существование по манифесту** и не ищет заголовок с таким именем. Путать нельзя: иначе получишь
ложный `CVAL-SEC` за «отсутствующий раздел `lib.json`».

### `facts_to_extract` — мост к кросс-документным проверкам

Перечисляет ровно те разделы, значения которых сравниваются с другими документами. Воркер
извлекает **дайджест** (список имён или ≤ 15 строк), не полный текст. Это и есть механизм, который
позволяет чекерам работать, не читая документы.

Типы фактов (`fact_specs` в `edges.yaml`): `spo_list`, `component_list`, `scenario_names`,
`item_names`, `section_digest`, `presence`, `version_value`, `file_json_keys`.

> `facts_to_extract` **вычисляется из рёбер** — не пиши его руками. Добавил ребро → перегенерируй
> (см. «Как добавить ребро»).

---

## Файл связей — `graph/edges.yaml`

```yaml
edges:
  - id: E-SPO-1
    type: spo                 # → определяет code
    code: CVAL-SPO
    scope: cross-doc          # КТО проверяет
    group: GRP-SPO            # какой edge-checker
    symmetric: true           # одно расхождение = одна находка, не две зеркальные
    a: {doc: about, section: "Необходимое программное обеспечение", fact: spo_list}
    b: {doc: installation-guide, section: "Чек-лист проверки корректности работы", fact: spo_list}
    rule: "Покрытие, не тождество: ..."   # уточнение семантики, читает чекер
```

### `scope` — кто исполняет ребро

| scope | Исполнитель | Что нужно |
|---|---|---|
| `intra-doc` | worker | только его документ |
| `cross-doc` | edge-checker | facts обеих сторон |
| `doc-existence` | orchestrator | манифест + один флаг `presence` |

### `type` → `code`

| type | code | Смысл |
|---|---|---|
| `spo` | `CVAL-SPO` | перечни СПО должны совпадать |
| `logical` | `CVAL-LOGIC` | логическая консистентность контента |
| `meta` | `CVAL-META` | согласованность с `db-models.json` / `deployment-units.json` |
| `include` | `CVAL-INC-X` (cross) / `CVAL-INC-IN` (intra) | включение контента одного раздела в другой |
| `link` | `CVAL-LINK` | ссылка ведёт в существующий документ |
| `dependency` | `CVAL-DEP` | наличие документа зависит от состава продукта |

Цветов больше нет: семантика в `type`, а не в стиле линии.

### `version_check` — сквозная сверка версий

Не ребро. Перечисляет документы, объявляющие версию продукта; все значения должны совпадать,
расхождение → `CVAL-VER`. Обрабатывает чекер группы `GRP-VER`.

### `edge_groups` — по чекеру на группу

Рёбра с общими документами объединены, чтобы не плодить субагентов: один чекер получает пути к
facts своей группы и проверяет все её рёбра. Сейчас: `GRP-SPO`, `GRP-DEPLOY`, `GRP-ARCH`,
`GRP-SCEN`, `GRP-RN`, `GRP-VER`.

---

## Рецепты

### Добавить раздел в документ

Правишь `graph/<doc_type>.yaml` → `sections`. Вложенность — только через `children`. Если раздел
может законно отсутствовать — поставь `flags: [cond]`, иначе он станет обязательным (ERROR при
отсутствии). Больше ничего менять не нужно.

### Добавить новый тип документа

1. Создай `graph/<doc_type>.yaml` с `doc_type`, `title`, `sections`.
2. Если документ опционален — `conditional_doc: true` и добавь ребро `type: dependency`
   в `edges.yaml` с триггером (что именно делает его обязательным).
3. Оркестратор подхватит его автоматически: он спавнит воркера на каждую папку с `index.md`.

### Добавить ребро

1. Впиши ребро в `edges.yaml`: `id`, `type`, `code`, `scope`, стороны `a`/`b` с `doc`, `section`,
   `fact`.
2. Припиши его к группе в `edge_groups` (или заведи новую — тогда добавь её в список групп в
   `SKILL.md` оркестратора, Phase 3b).
3. **Перегенерируй `facts_to_extract`** в файлах затронутых документов — иначе воркер не извлечёт
   факт, и чекеру нечего будет сравнивать:

```python
import yaml, pathlib, collections
e = yaml.safe_load(open('graph/edges.yaml'))
extract = collections.defaultdict(dict)
for edge in e['edges']:
    for side in ('a', 'b'):
        s = edge.get(side)
        if not s or 'doc' not in s or not s.get('fact'):
            continue
        extract[s['doc']].setdefault(s.get('section') or '__doc__', set()).add(s['fact'])
    if t := edge.get('trigger'):
        extract[t['doc']].setdefault(t['section'], set()).add(t.get('fact', 'presence'))
for d in e['version_check']['collect_from']:
    extract[d].setdefault('version', set()).add('version_value')

for name, ex in extract.items():
    p = pathlib.Path(f'graph/{name}.yaml')
    doc = yaml.safe_load(open(p))
    doc['facts_to_extract'] = {
        k: {'fact': sorted(v)[0] if len(v) == 1 else sorted(v),
            'spec': e['fact_specs'].get(sorted(v)[0], '')}
        for k, v in sorted(ex.items())
    }
    with open(p, 'w') as f:
        yaml.dump(doc, f, allow_unicode=True, sort_keys=False, width=100)
```

### Проверить целостность после правки

```python
import yaml, pathlib
e = yaml.safe_load(open('graph/edges.yaml'))
docs = {p.stem for p in pathlib.Path('graph').glob('*.yaml')} - {'edges'}

# все документы из рёбер существуют?
refd = {s['doc'] for edge in e['edges'] for k in ('a','b','trigger')
        if (s := edge.get(k)) and 'doc' in s}
assert not refd - docs, f"нет graph-файла: {refd - docs}"

# каждый cross-doc эндпоинт покрыт facts_to_extract?
for edge in e['edges']:
    if edge.get('scope') != 'cross-doc':
        continue
    for k in ('a', 'b'):
        s = edge.get(k)
        if not s or not s.get('section') or not s.get('fact'):
            continue
        fte = yaml.safe_load(open(f"graph/{s['doc']}.yaml")).get('facts_to_extract', {})
        assert s['section'] in fte, f"{edge['id']}: {s['doc']}::{s['section']} не извлекается"

# группы ссылаются на существующие рёбра?
ids = {edge['id'] for edge in e['edges']}
for g, spec in e['edge_groups'].items():
    for eid in spec.get('edges', []):
        assert eid in ids or eid.startswith('N-'), f"{g} → несуществующее ребро {eid}"
print("граф консистентен")
```

---

## Чего не делать

- **Не заводить второй источник истины.** Диаграмма для людей — можно, но только если она
  генерируется из графа. Две правки руками неизбежно разъедутся (именно так появились ложные
  срабатывания в первой версии).
- **Не писать `facts_to_extract` руками** — вычисляй из рёбер, иначе воркер и чекер разойдутся.
- **Не путать `files` и `sections`** — JSON-артефакты проверяются по манифесту, а не как заголовки.
- **Не кодировать вложенность в имени** (`___Раздел`) — только `children`.
- **Не добавлять раздел без `flags`, если он необязателен** — получишь поток ложных ERROR.
