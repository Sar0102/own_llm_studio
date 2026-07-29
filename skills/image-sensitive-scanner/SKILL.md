---
name: image-sensitive-scanner-orchestrator
description: Orchestrator for scanning documentation images for sensitive information. Discovers every image and diagram file under resources/ folders in the repository, dispatches one scanner subagent per file (parallel batch, because base64 images are large), and merges their on-disk results into image-validator.json. Independent of documentation consistency validation.
---

# Image Sensitive Scanner — Orchestrator

## TWO SEPARATE TOOL FAMILIES — never mix them

**Repository tools (remote git):** `get_file_list`, `get_single_file`, `get_multiple_files`.
They take `repository_url` + `branch` + a **repo-relative** `file_path`. They only reach the git
repository. Never pass them a local path or a `file:///...` URL — that raises `Unsupported URL format`.

**Local workspace tools (disk):** `ls`, `read_file`, `write_file`, `glob`, `grep` — a single
**absolute** path starting with `/`. Use these for the manifest, scanner results and the final report.

**Do not write or run scripts.** There is no shell tool.

## YOU ARE A DISPATCHER (hard constraints)

- You **never read image files yourself**. A base64 image is huge; loading even one would blow your
  context. Every file is scanned by a `image-sensitive-scanner` subagent — one file per subagent.
- The only way to get a scan result is to spawn a subagent. There is no fallback.
- Communication is **through files on disk**: subagents write JSON, you read it back after they
  finish. Their chat reply is just a `written: <path>` confirmation.
- **Spawn in batches**: emit ALL spawn calls in a single turn (one assistant turn with many parallel
  spawn tool-calls). Never spawn one, wait, then spawn the next.
- Spawn only `image-sensitive-scanner`. Never delegate to `general-purpose`.

## HOW TO SPAWN A SUBAGENT

A subagent starts with a blank context — it sees **only the task description you write**. Every task
description **must begin with this exact line**:

```
REPO: <repository_url> BRANCH: <branch> FILE: <resources file path>
```

Then add, each on its own line:

```
skill_dir: <absolute path to this skill's root>
product: <product name>
output_path: <absolute path>/scans/<file_id>.json
```

- `repository_url` / `branch` — verbatim from the workflow input. Never blank, never guessed.
- `skill_dir` — the directory containing your own SKILL.md (its absolute path is in your Skills
  list). The scanner reads `<skill_dir>/sensitive-data.md` from there. Without it, subagents hunt the
  filesystem with `glob`/`ls` and die on the execution timeout.
- `product` — the product name, so the scanner does not flag the product's own name as a leak.

Concrete example:

```
REPO: https://portal.works.prod.sbt/ssd/tools/sc/pvm/pegas-doc BRANCH: release/6.6.200 FILE: documentation/documents/architecture/resources/diagram2.png
skill_dir: /Users/<...>/skills/image-sensitive-scanner
product: pegas
output_path: /tmp/image-scanner/scans/architecture__resources__diagram2.png.json
```

## Canonical sources

- **`<skill_dir>/sensitive-data.md`** — the category dictionary (SD-01…SD-11) and the false-positive
  exclusions. The scanners read it; you don't need to.

## Paths

| Purpose | Path |
|---|---|
| Discovery root | `documentation/` |
| Manifest (you write) | `{workspace_path}/tmp/image-scanner/manifest.json` |
| Scanner results (subagents write) | `{workspace_path}/tmp/image-scanner/scans/<file_id>.json` |
| Final report (you write) | `{workspace_path}/reports/image-validator.json` |

`workspace_path` = `/docstorage/tmp/{{workflow.uid}}/`. `<file_id>` = the repo path relative to
`documents` with `/` → `__` (e.g. `architecture__resources__diagram2.png`).

## Workflow

### Phase 0: Discovery

1. Read `repository_url` and `branch` from the workflow input; note your **`skill_dir`**; derive the
   **product name** from the repository slug (`.../sc/pvm/pegas-doc` → `pegas`). Capture these four
   values once and pass them verbatim into every task description.
2. Enumerate the file tree under `documentation/` with **one** recursive repository listing call
   (no file contents, no per-directory fan-out).
3. Write **`manifest.json`** — a flat JSON array of the repo-relative paths of every file under any
   `resources/` folder (`**/resources/**`) with an image or diagram extension:
   `.png .jpg .jpeg .gif .bmp .webp .svg .drawio`. **Dedupe by path** — the same image referenced
   from several documents is scanned once.
4. Create the `scans/` directory.

If no such files exist, write an empty report and stop.

### Phase 1: Dispatch (single parallel batch)

Emit, in ONE turn, one `image-sensitive-scanner` spawn per file from the manifest, each with the
task description described above.

Large batches are fine — subagents are independent. What matters is that you never read the images.

### Phase 2: Join & Completeness

Wait until every scanner has finished, then confirm a JSON exists on disk for each dispatched file.
Missing → retry once, else record:

```json
{ "code": "SENS-WORKER", "severity": "WARNING", "path": "<file>",
  "message": "Субагент не вернул результат по `<file>`." }
```

### Phase 3: Merge & Write

**You do this yourself** — a few `read_file` calls and one `write_file`. No scripts, no delegation.

1. `glob` `.../scans/*.json`, `read_file` each.
2. Concatenate all `issues`, plus your own Phase 2 issues.
3. Deduplicate (`code` + `path` + `message`); sort by severity (`ERROR` → `WARNING` → `INFO`), then `path`.
4. `write_file` the report to `{workspace_path}/reports/image-validator.json`.

If `glob` comes back empty where results were expected, do **not** silently write an empty report —
record a `SENS-WORKER` issue per missing file so the failure is visible.

> **All JSON field values are serialized as strings, even numeric ones; `null` stays `null`.**

```json
{
  "title": "Чувствительная информация в изображениях",
  "priority": "15",
  "issues": [
    {
      "code": "SENS-FOUND",
      "severity": "ERROR",
      "path": "documentation/documents/architecture/resources/deploy-scheme.png",
      "message": "В файле `documentation/documents/architecture/resources/deploy-scheme.png` обнаружены признаки чувствительной информации: SD-04 — ссылки на внутренние ресурсы (2 вхождения), подписи узлов на схеме развертывания.",
      "position": null,
      "advice": "Заменить внутренние хосты на обезличенные имена узлов"
    }
  ]
}
```

Do not modify issue contents during merge — only concatenate, dedupe, sort.

## Codes

| Code | Severity | Meaning |
|---|---|---|
| `SENS-FOUND` | ERROR / WARNING (per category) | Sensitive information found in the file |
| `SENS-SKIP` | INFO | File not scanned (over the size limit, unsupported type, decode failure) |
| `SENS-WORKER` | WARNING | A scanner subagent returned no result |

## Rules

1. Never read image files — one scanner subagent per file, always.
2. One recursive listing in Phase 0; after the manifest is written, no further listing calls.
3. Spawn the whole batch in a single turn; never serialize.
4. Read results from disk after subagents finish, never from their chat replies.
5. Scan only files under `resources/` folders inside `documentation/`.
6. All JSON field values are strings; `null` stays `null`. Findings are written in Russian,
   identifiers in English.
