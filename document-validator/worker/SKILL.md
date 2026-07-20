---
name: document-validator-worker
description: Worker for parallel documentation validation. Receives ONE document folder (index.md plus its fragment files), assembles the full section tree, validates it against that doc type's graph file, checks includes and references against the repository manifest, extracts cross-document facts, and writes a per-document JSON to disk. Invoked by the document-validator-orchestrator.
---

# Document Validator — Worker

## REQUIRED STEPS (fetch the whole document, then validate)

You validate ONE **document**. A document is NOT one file. It is `index.md` plus the files it
**links to** — `index.md` works like a table of contents: it links out to chapter files, and inside
those a "Содержание" section links further to sub-section files. A section is present if it exists in
**any** of these linked files. Judging `index.md` alone is the main cause of false "missing section"
errors.

**Turn 1 — start at the entry point (parallel):**
1. `get_single_file(repository_url, branch, <DOC>/index.md)` — the document's table of contents.
2. `read_file(<skill_dir>/graph/<doc_type>.yaml)` — the expected section tree (small file).
3. `read_file(<manifest_path>)` — the repo file list (or `grep` it later if huge).

**Turn 2 — follow the links and pull in the whole document:**
4. Collect every **in-repo link** from `index.md` and from any "Содержание" / contents list inside
   it — these are the chapter and sub-section files that make up the document. Resolve them
   (see "Resolving links"), then fetch them all in **one** `get_multiple_files(repository_url,
   branch, [paths])` call.
5. If a fetched chapter file itself contains a "Содержание" / contents list pointing to more in-repo
   files, collect those too and fetch them in **one** more `get_multiple_files` call. At most two
   such link-following rounds — the document is shallow; do not recurse endlessly.

**Turn 3 — assemble, validate, write:**
6. Build ONE combined section tree from `index.md` + every file you pulled in, tracking which file
   and line each heading came from. Validate this **assembled** tree against the graph, extract
   facts, `write_file(<output_path>)`, reply `written: <output_path>`.

Do not explore the filesystem blindly. An empty result means you skipped the fetch — that is a bug,
not a clean document.

## Tools — two separate families, never mix them

**Repository (remote git):** `get_single_file(repository_url, branch, file_path)` and
`get_multiple_files(repository_url, branch, file_paths)`. Pass `repository_url`/`branch` from the
task line **verbatim**. Never give them a local path or a `file:///...` URL — that fails with
`Unsupported URL format`.

**Local disk:** `read_file`, `write_file`, `glob`, `grep`, `ls` — **absolute** paths starting with
`/`. Use these for `<skill_dir>/graph/<doc_type>.yaml`, the manifest, and `output_path`.

Existence of include/reference targets is checked **against the manifest** (a local file), never by
probe fetches. There is no shell tool: never write or run scripts.

## Input (from orchestrator)

The task text begins with:

```
REPO: <repository_url> BRANCH: <branch> DOC: <document folder>
```

Parse the three values and use them verbatim. `DOC:` is a **folder** (e.g.
`documentation/documents/about`), not a file. The rest of the task carries:

| Param | Description |
|---|---|
| `skill_dir` | **Absolute** path to the skill root. Read `<skill_dir>/graph/<doc_type>.yaml` — do not search for it |
| `doc_type` | Your document type (`about`, `architecture`, …). Names the graph file you read |
| `output_path` | **Absolute** path where you write your result JSON |
| `manifest_path` | **Absolute** path to `manifest.json` — every repo-relative file path under `documentation/` |

You are only spawned for document types that exist in the graph (the orchestrator skips unknown
folders). If you nonetheless find no graph file for your `doc_type`, write an empty result
(`issues: []`, `facts: {}`) and stop — never invent requirements for a type you don't know.

## Assembling the document

A document = `index.md` + every file it links to (chapters), + every file those link to via a
"Содержание" list (sub-sections). A section counts as **present** if it appears in *any* of these
files. Build one combined heading tree, tracking which file and line each heading came from (needed
for `position`).

Recognise a section heading in **any** of these forms — do not look only for `##` markdown headings:
- a markdown heading (`#`…`######`) at the top of a linked file — its text is the section/subsection
  name (e.g. a file whose H1 is «Сценарии администрирования»);
- an item in a "Содержание" / contents list that links to another file — the **link target's own
  heading** is the section name;
- a list item or table row acting as a heading in docs that use `• ___Название` style.

Never judge one file on its own. On the screen example, `administration-scenarios.md` contains only a
"Содержание" with links — the real subsections («Сценарий администрирования», «Как определить версию
продукта») live in the linked files. You must follow those links and take the subsections from the
target files. Reporting them missing because they are not headings inside `index.md` is the exact bug
to avoid. Missing-section findings are made against the **assembled** tree, never against one file.

## Severity & Conditionality Rules (apply before emitting anything)

The report contains **only real problems: ERROR and WARNING**. Do **not** emit `INFO` or
`SUGGESTION` findings at all — a legitimately-absent section (`std_exception_reason`) or a section
that didn't exist in this version is simply **not written to the output**, not reported as a note.

| Situation | Severity / Action |
|---|---|
| Mandatory section missing from the **assembled** tree | `ERROR` (`CVAL-SEC`/`CVAL-SUBSEC`) |
| Metainfo contains `std_exception_reason` | **suppress** — no finding at all (not even INFO) |
| Section flagged `cond`, or a note says "при наличии…" | `WARNING` (`CVAL-COND`) or skip — never `ERROR` |
| Section flagged `version_aware`, didn't exist in this version | **skip** — no finding (no SUGGESTION) |
| Section flagged `gen` (auto-generated) | do **not** flag as missing |
| Section present via a linked file | counts as **present** |
| Marker `uml` but a real raster image instead of a diagram | `WARNING` (`CVAL-UML-IMG`) |
| Entries under `files` (`lib.json`, `agent.json`, …) | **files, not headings** — check via manifest; never `CVAL-SEC` |

A `.drawio` file, a `.puml`/PlantUML block, or an embedded editable diagram **satisfies** marker
`uml` — it is a UML diagram, not "an image". Only a plain raster screenshot (`.png`/`.jpg`) where a
diagram is expected triggers `CVAL-UML-IMG`. A link like `logic-diagram.md?display=source` pointing
at a `.drawio` is a diagram — do not flag it.

## Codes you may emit (the full dictionary is not needed)

| Code | Severity | When | `message` template (Russian) |
|---|---|---|---|
| `CVAL-SEC` | ERROR | Mandatory section missing | Отсутствует обязательный раздел «{section}» в `{doc}` ({position}). |
| `CVAL-SUBSEC` | ERROR | Mandatory subsection missing | Отсутствует обязательный подраздел «{subsection}» раздела «{parent}» в `{doc}` ({position}). |
| `CVAL-NEST` | WARNING | Subsection under the wrong parent | Подраздел «{subsection}» расположен не под «{parent}» в `{doc}` ({position}). |
| `CVAL-COND` | WARNING | Conditional section absent | Условный раздел «{section}» отсутствует в `{doc}` — зависит от {reason}, не ошибка. |
| `CVAL-UML-IMG` | WARNING | Raster image instead of a diagram | В разделе «{section}» (`{doc}`, {position}) ожидается UML-диаграмма, присутствует растровое изображение. |
| `CVAL-INC` | ERROR | `include` target not in manifest | `include` из «{section}» (`{doc}`) ссылается на `{target}` — файла нет в манифесте репозитория. |
| `CVAL-REF` | ERROR | Reference not in manifest | Ссылка на `{target}` из «{section}» (`{doc}`, {position}) не разрешается: файла нет в манифесте. |
| `CVAL-PATH` | WARNING | Wrong path, file exists elsewhere | Ссылка на `{target}` из «{section}» (`{doc}`, {position}) указывает неверный путь — файл существует по `{actual_path}`. |
| `CVAL-INC-IN` | WARNING | Intra-doc edge unsatisfied | Раздел «{section}» (`{doc}`) должен опираться на «{required_section}», но не содержит его. |
| `CVAL-NOTE` | WARNING | Intra-doc note violated | Не выполнено требование примечания графа для «{section}» (`{doc}`): {note}. |

Formatting: paths/identifiers in backticks, section names in «ёлочки» exactly as spelled in the graph
file. `{doc}` always starts with `documentation/` and names the **file** the finding is in (index.md
or the fragment). Drop `({position})` entirely when the position is unknown — never write `(null)`.
`advice`: imperative, one action, else `null`. Text never changes severity.

## Which links to check (only same-repo, same-branch) — and which to skip

Two kinds of links must be handled differently:

- **Structural links** — the contents lists in `index.md` and "Содержание" that point to chapter and
  sub-section files of THIS document. You **follow** these to assemble the document (see above). They
  are never "broken reference" findings; they are how the document is built.
- **Plain references** in body text — these are what you check for existence, but **only** if they
  point inside the same repository and branch. Everything else is out of scope: do **not** flag it.

**Skip (never emit CVAL-INC/CVAL-REF) when the link is:**
- an external URL — any `http://` or `https://` to another host (e.g. `docs.sbt/...`,
  `portal.works.prod.sbt/...`). Not your repository, not your concern.
- a link into a **different repository or branch** than the one you were given (`REPO:` / `BRANCH:`).
- a pure `#anchor` (same-page link) or a `mailto:`.
- an external/generated resource: `/info/*.json`, `required-software.json`, `rn-*.json`.

**Check only** links that resolve to a file **in this repo** under `documentation/`:
a. Normalize: strip `#anchor` and `?query` (e.g. `?display=source`); drop leading `./`; resolve `../`
   relative to the containing file's directory; express repo-relative with the `documentation/` prefix.
b. Exact match in the manifest → the target exists, nothing to report.
c. No exact match → look up the basename in the manifest (`grep` it): found elsewhere → `CVAL-PATH`
   (WARNING); found nowhere → `CVAL-REF` / `CVAL-INC` (ERROR).
d. Never verify existence with `get_single_file` — a network error is indistinguishable from a
   missing file and produces false ERRORs.

## Intra-doc edges & notes

Your graph file may carry `edges` with `scope: intra-doc` (for `architecture`: sections that must
build on «Компоненты») → `CVAL-INC-IN`, and `notes` with `scope: intra-doc` → `CVAL-NOTE`.
Notes marked `scope: cross-doc` are **not yours** — edge-checkers handle them; you have no other
documents.

## Fact Extraction

Your graph file lists `facts_to_extract`: exactly the sections whose facts other documents are
compared against, each with its `fact` type and a `spec` telling you what to pull out. Extract those
and nothing else. Key each entry by the **section name as spelled in the graph file**.

Values are digests — lists of names, or ≤ 15 lines of key statements — **not** the full section text.
The edge-checker compares only this, so digest quality decides whether cross-document checks work.

```json
{
  "version":              { "value": "D-6.0.0", "position": "index.md front-matter L4" },
  "Необходимое программное обеспечение": {
                            "value": ["python3.11", "postgresql-15"],
                            "position": "required-software.md L20-31" },
  "Сценарии отказа":      { "value": ["сбой БД", "потеря сети"], "position": "other-issues.md L120-140" },
  "attachments":          [ { "path": "documentation/documents/architecture/resources/scheme.png",
                              "referenced_from": "Компонентно-логическая диаграмма, logic-diagram.md L45" } ]
}
```

If a listed section is genuinely absent, set `"value": null` (keep the key). Collect `attachments`
(binary/graphic files referenced by the document) but **never read their content** — scanners do that.

## Output

Write to `output_path`. **All JSON field values are strings, even numeric ones; `null` stays `null`.**

```json
{
  "doc": "documentation/documents/installation-guide",
  "doc_type": "installation-guide",
  "facts": {},
  "issues": [
    {
      "code": "CVAL-SEC",
      "severity": "ERROR",
      "path": "documentation/documents/installation-guide/index.md",
      "message": "Отсутствует обязательный раздел «Удаление» в `installation-guide`.",
      "position": null,
      "advice": "Добавить раздел «Удаление»"
    }
  ]
}
```

`path` names the specific file the finding is in. `message`/`advice` are written in Russian;
technical terms and identifiers stay in English.

## Rules

1. One worker = one document folder. Two repository calls total: `get_single_file` (index.md) +
   `get_multiple_files` (fragments). No probe fetches, no re-reads.
2. Judge sections against the **assembled** tree, never against one fragment.
3. Apply the Severity & Conditionality table before emitting any issue.
4. Include/reference existence — manifest only, with basename fallback.
5. Do not read binary attachments — list them in `facts.attachments`.
6. No cross-document comparison; extract facts only.
7. Always `write_file` to `output_path` (empty `issues` if clean); reply is one confirmation line.
8. Findings in Russian; identifiers in English; all JSON values as strings.
