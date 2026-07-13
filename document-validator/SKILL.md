---
name: document-validator-orchestrator
description: Orchestrator for parallel documentation validation. Discovers the document folders under documentation/documents, builds a repository manifest, dispatches one worker PER DOCUMENT FOLDER and one scanner PER resources file (parallel batch), then dispatches edge-checkers for the cross-document consistency groups in graph/edges.yaml, and merges every subagent's on-disk result into consistency-validator.json.
---

# Document Validator — Orchestrator

## HOW TO SPAWN A SUBAGENT (read first — the task text carries all the data)

A subagent starts with a blank context. It sees **only the task description you write** — nothing
from your context, no separate parameters, no repository URL, no path unless you put them in the
task text. So every `task` description **must begin with this exact line**:

```
worker:   REPO: <repository_url> BRANCH: <branch> DOC: <document folder>
scanner:  REPO: <repository_url> BRANCH: <branch> FILE: <resources file>
```

- `<repository_url>` and `<branch>` — copy verbatim from the workflow input. Never blank, never guessed.
- `DOC:` — a **folder** (`documentation/documents/about`). The worker validates the whole document:
  `index.md` plus the fragments it includes. Never point a worker at a single fragment.
- `FILE:` — one `resources/` file for a scanner.

**Then always add `skill_dir` — an absolute path.** Subagents cannot resolve relative paths: every
filesystem tool requires an absolute path starting with `/`. Without `skill_dir` they waste dozens of
`glob`/`ls` calls hunting for their graph file and get killed by the execution timeout. Your own
SKILL.md absolute path is in your Skills list; its directory is the skill root.

Concrete worker example:

```
REPO: https://portal.works.prod.sbt/ssd/tools/sc/sowa/sowa_docs BRANCH: release/D-5.4.2 DOC: documentation/documents/about
skill_dir: /Users/<...>/svc-ai-agent/skills/document-validator
doc_type: about
output_path: /tmp/document-validator/files/about.json
manifest_path: /tmp/document-validator/manifest.json
```

`doc_type` tells the worker which graph file to read (`<skill_dir>/graph/<doc_type>.yaml`) — pass it
always. Every path (`skill_dir`, `output_path`, `manifest_path`) must be **absolute**.

## TWO SEPARATE TOOL FAMILIES — never mix them

This is the single most common failure. There are two completely different worlds:

**Repository tools (remote git):** `get_file_list`, `get_single_file`, `get_multiple_files`.
They take `repository_url` + `branch` + a **repo-relative** `file_path` (e.g.
`documentation/documents/about/index.md`). They only reach the git repository. Never pass them a
local path, and never a `file:///...` URL — that raises `Unsupported URL format`.

**Local workspace tools (disk):** `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`.
They take a single **absolute** path starting with `/` (e.g. `/tmp/document-validator/files/x.json`).
Use these — and only these — for everything on disk: `manifest.json`, worker/scanner/checker result
JSONs, the skill files under `skill_dir`, and the final report.

Rule of thumb: repo content → repository tools. Anything under `/tmp`, `/Users`, or any local path →
local tools. Reading `/tmp/document-validator/files/*.json` with `get_multiple_files` is always wrong;
use `glob` + `read_file`.

**Do not write or run scripts.** There is no shell tool. Never attempt `run_shell_command`, never
generate a Python file to process results. Every step here is done with the tools listed above.

## YOU ARE A DISPATCHER (hard constraints)

You coordinate subagents. You do NOT do their work. Specifically:

- You MUST NOT read document content, build section trees, compare sections, resolve includes, or
  scan files yourself. If you catch yourself reading a document or validating it, you have broken
  your role — stop and dispatch a subagent instead.
- The ONLY way to obtain any per-file, per-group, or per-scan result is to **spawn the
  corresponding subagent**. There is no fallback where you produce results directly.
- **Spawn only the three named subagents**: `document-validator-worker`,
  `document-validator-scanner`, `document-validator-edge-checker`. Never delegate to
  `general-purpose` — it does not know this skill and will improvise (write scripts, misuse tools).
  Anything not covered by those three (discovery, manifest, doc-existence edges, merge) you do yourself.
- All inter-agent communication is **through files on disk**. Subagents write their JSON to disk;
  you read those files back **only after they finish**. You never rely on a subagent's chat reply
  for its result (their reply is just a `written: <path>` confirmation).
- **Spawn in batches, not one-by-one.** For each wave, emit ALL spawn calls for that wave in a
  single turn (one assistant turn containing many parallel spawn tool-calls). Do NOT spawn one
  subagent, wait for it, then spawn the next — that serializes the whole run. Issue the whole batch,
  then wait for the batch to complete.
- Self-check before finishing: did you avoid every file-read / validation tool? Did you dispatch
  every unit? Did you read results from disk (not from replies)? If any is no, fix it.

## Canonical sources (skill root)

- **`<skill_dir>/graph/edges.yaml`** — every cross-document consistency edge (with `scope`, `code`,
  `group`), the fact specs, the version check and the edge groups. **This is the one you read.**
- **`<skill_dir>/graph/<doc_type>.yaml`** — one file per document type: its section tree, markers,
  flags, intra-doc notes and the facts its worker must extract. These are for the **workers** —
  you never read them; you just tell each worker its `doc_type`.
- **`<skill_dir>/error-codes.md`** — finding codes, `message` templates, placeholder rules.
- **`<skill_dir>/sensitive-data.md`** — sensitive-information dictionary for scanning `resources/`.

If anything in this file disagrees with the graph files, the graph files win.

## Subagents you dispatch

| Subagent (`name`) | Unit of work | Reads | Writes |
|---|---|---|---|
| `document-validator-worker` | one **document folder** (index.md + fragments) | its files + `graph/<doc_type>.yaml` + manifest | `files/<doc_type>.json` |
| `document-validator-scanner` | one `resources/` file | its file + sensitive-data.md | `scans/<file_id>.json` |
| `document-validator-edge-checker` | one edge group | `graph/edges.yaml` + that group's facts files | `edges/<group_id>.json` |

## Paths

| Purpose | Path |
|---|---|
| Discovery root | `documentation/documents` |
| Repository manifest (you write) | `{workspace_path}/tmp/document-validator/manifest.json` |
| Per-file results (workers write) | `{workspace_path}/tmp/document-validator/files/<file_id>.json` |
| Edge-group results (edge-checkers write) | `{workspace_path}/tmp/document-validator/edges/<group_id>.json` |
| Scanner results (scanners write) | `{workspace_path}/tmp/document-validator/scans/<file_id>.json` |
| Final report (you write) | `{workspace_path}/reports/consistency-validator.json` |

`workspace_path` = `/docstorage/tmp/{{workflow.uid}}/`. `<file_id>` = path relative to `documents`
with `/` → `__` (e.g. `developer-guide__index.md`, `architecture__resources__scheme.png`).

## Workflow

### Phase 0: Discovery & Manifest

0. Read `repository_url` and `branch` from the workflow input, and note your **`skill_dir`**: the
   directory containing your own SKILL.md, whose absolute path is shown in your Skills list (e.g.
   `/Users/<...>/skills/document-validator`). `graph/edges.yaml`, `error-codes.md` and `sensitive-data.md`
   sit in that directory. These three values — `repository_url`, `branch`, `skill_dir` — are the
   canonical constants for the whole run: **capture them once and pass them, verbatim, into every
   task description you write.** Read `<skill_dir>/graph/edges.yaml` yourself (edges + groups). The per-document section trees live in
   `<skill_dir>/graph/<doc_type>.yaml` — those are for the workers, you never read them.
1. Use the remote repository integration (source-control tool) for that `repository_url`/`branch` —
   **do not clone locally**.
2. Enumerate the **full file tree** under `documentation/` via **one** repository listing call (no
   file contents; use the recursive listing from the root — do not fan out per-directory listings).
   If `documentation/documents` does not exist — stop and report no documents folder.
3. Write **`manifest.json`**: a flat JSON array of every repo-relative file path under
   `documentation/`. The manifest is the single existence-check source for all subagents — after it
   is written, no further listing calls are made anywhere in the run.
4. From the manifest derive two work lists:
   - **documents**: the distinct folders under `documentation/documents` that contain an `index.md`
     (e.g. `documentation/documents/about`, `.../architecture`, …). **One worker per folder — not per
     file.** A document is `index.md` plus the fragment `.md` files it includes; validating a fragment
     on its own is meaningless (it holds one section, and the worker would report every other section
     as missing). This keeps the run to ~12 workers instead of ~100.
   - **scan targets**: every file under any `resources/` folder (`**/resources/*`) with extensions
     `.png .jpg .jpeg .gif .bmp .webp .svg .drawio` → **dedupe by path** → one scanner each.
5. Create the tmp directories (`files/`, `edges/`, `scans/`).

### Phase 1: Wave 1 — workers + scanners (single parallel batch)

Emit, in ONE turn, a spawn call for every **document folder** AND every scan target. Each task
description begins with its `REPO:/BRANCH:/…` line (see the top of this file). Then append:

- **worker** (one per document folder): `DOC:` = the folder; then `skill_dir`, `doc_type`,
  `output_path` = `.../files/<doc_type>.json`, `manifest_path`.
- **scanner** (one per resources file): `FILE:` = that file; then `skill_dir`,
  `output_path` = `.../scans/<file_id>.json`.

Workers and scanners are independent — they belong in the same wave. Do not wait between spawns.

The `REPO:/BRANCH:/FILE:` prefix is a hard contract: a subagent that does not receive it cannot
access the repository and will fail. Build the line for every spawn without exception.

Workers and scanners are independent — they belong in the same wave. Do not wait between spawns.

### Phase 2: Join & Completeness

- Wait until every dispatched worker and scanner has finished.
- Confirm the output JSON exists on disk for every dispatched unit. Missing → retry once, else record:
  ```json
  { "code": "CVAL-WORKER", "severity": "WARNING", "path": "documentation/documents/<file>",
    "message": "Субагент не вернул результат по `<file>`." }
  ```
- Build the **facts index**: `doc_type → /…/files/<doc_type>.json` (paths only; you do not read
  facts content, except the single `presence` flags needed in Phase 3a).

### Phase 3a: Doc-existence edges (you, from the manifest)

Handle `graph/edges.yaml` edges with `scope: doc-existence` — these need only the manifest plus the single
`presence` flag of a trigger section from the architecture facts file (one narrow field read):

- `E-DEP-1`, `E-DEP-2` → `CVAL-DEP`: trigger section is non-empty but the required doc is absent from
  the manifest → WARNING (the doc is optional, so not ERROR).
- `E-LINK-1` → `CVAL-LINK`: the architecture link section points to `deployment`, absent from the
  manifest → ERROR.

### Phase 3b: Wave 2 — edge-checkers (single parallel batch)

Edge-checkers do **not** touch the repository — they read facts files from disk. So their task text
does **not** use the `REPO:/BRANCH:/FILE:` line; instead each task description carries the paths they
need — all **absolute**. Emit, in ONE turn, a spawn call for every group in `graph/edges.yaml → edge_groups`
(GRP-SPO, GRP-DEPLOY, GRP-ARCH, GRP-SCEN, GRP-RN, GRP-VER). For each
`document-validator-edge-checker` put in the task description:

- `skill_dir` — absolute path to the skill root (they read `<skill_dir>/graph/edges.yaml` and
  `<skill_dir>/error-codes.md`; without it they hunt the filesystem and time out).
- `group_id`.
- `facts_paths` — map `doc_type → absolute path to facts JSON` for that group's docs only; `null` if
  the doc is absent from the repository (the checker applies conditionality rules).
- `output_path` = `.../edges/<group_id>.json`.

Wait until every edge-checker has finished.

### Phase 4: Merge & Write

**You do this yourself.** Never delegate the merge to a subagent — and never to `general-purpose`.
It is a few `read_file` calls and one `write_file`. Use only local tools; write no scripts.

1. `glob` each result directory (`.../files/*.json`, `.../edges/*.json`, `.../scans/*.json`) and
   `read_file` each result. If `glob` comes back empty where results were expected, the subagents
   failed — do **not** silently produce an empty report: record a `CVAL-WORKER` issue per missing
   unit so the failure is visible in the output.
2. Concatenate all `issues` arrays, plus your own Phase 2/3a issues.
3. Deduplicate identical issues (`code` + `path` + `message`).
4. Sort by severity (`ERROR` → `WARNING` → `SUGGESTION` → `INFO`), then by `path`.
5. `write_file` the final report.

> **All JSON field values are serialized as strings (type `string`), even numeric ones — e.g.
> `"priority": "15"`. `null` stays `null`.**

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

Save **only** to `{workspace_path}/reports/consistency-validator.json`, using `write_file`. Do not
modify issue contents during merge — only concatenate, dedupe, sort.

## Rules

1. Never read document content; never read facts files whole — only path lists, statuses, and the
   single `presence` flags for Phase 3a.
2. One worker = one file; one scanner = one file; one edge-checker = one group.
3. File existence is checked **only** against `manifest.json` — no probe fetches.
4. Spawn each wave as a single parallel batch; never serialize spawns.
5. Read subagent results **from disk after they finish**, never from their chat replies.
6. Finalize only after all subagents are accounted for (or recorded as `CVAL-WORKER`).
7. Do not modify issue contents during merge — only concatenate, dedupe, sort.
8. Do not scan anything outside `documentation/`.
9. All JSON field values are strings, even numeric; `null` stays `null`.

## Finding Writing Guidance

Finding text rules, codes, templates and placeholders are defined **only** in `<skill_dir>/error-codes.md`.
Before writing any of your own findings (Phase 2/3a), open it and take the `code`, template and
placeholder rules from there. In short: `message`/`advice` in Russian, technical terms in English;
be specific (file + section + line); no modality or emotion; the text never changes severity.
