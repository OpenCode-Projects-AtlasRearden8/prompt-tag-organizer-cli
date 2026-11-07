# STATUS.md — prompt-tag-organizer

## What was built

`prompt-tag-organizer` (`pto`) — a zero-dependency, local-first Python CLI
that keeps one tidy library of your best prompts in plain Markdown and JSON.

- **`scan DIR`** — lists every `.md`/`.json` prompt file with its tags, task, and score (`--json` for machine-readable output).
- **`tag FILE --tags a,b --task ... --score N`** — adds/updates frontmatter in place (`--dry-run` previews; `--add-tags` merges; `--remove` strips frontmatter; targeted JSON items via `--index`/`--group`).
- **`search DIR --tag TERM`** — fuzzy tag search with typo tolerance (`emial` finds `email`); `--strict` for exact matches.
- **`dupes DIR --threshold 0.9`** — flags near-duplicate prompts (normalized-text similarity via token-set + SequenceMatcher).
- **`export DIR -o index.html`** — a self-contained, browsable HTML index with tag filter buttons, scores, task notes, full prompt text, near-duplicate warnings, escaped output. Built with the Python standard library only.
- **`ai-tag DIR`** — optional AI tagging via any OpenAI-compatible endpoint. Default is Ollama on `localhost:11434` (no API key); suggestions are shown as a dry run first, `--apply` writes `tags`/`task` into Markdown frontmatter or JSON with graceful failure when the server is unreachable.

Package layout: `prompt_tag_organizer/` with `parser.py` (frontmatter parse/render + scanning), `search.py`, `dedupe.py`, `export.py`, `ai.py`, `cli.py` (argparse). Installs both `prompt-tag-organizer` and `pto` console commands.

Distinct by design: `prompt-tag-organizer` is for **organizing/tagging** your existing prompt library — not for testing prompts (prompt-lab-cli) or shipping them as distributable packs (snippet-pack-builder-cli).

## How to run it

```bash
pip install .            # Python 3.9+, no external dependencies
pto --version
pto scan ~/prompts
pto tag ~/prompts/idea.md --tags email --task "cold email" --score 4
pto search ~/prompts --tag emial
pto dupes ~/prompts --threshold 0.85
pto export ~/prompts -o index.html
# optional local AI tagging (Ollama):
ollama pull llama3.2 || true
pto ai-tag ~/prompts             # dry-run suggestions
pto ai-tag ~/prompts --apply
```

## Verification results

- `python -m pytest` — **46 passed, 0 failed** (tests cover frontmatter parsing/round-trips, JSON loading variants, fuzzy search, duplicate detection, HTML export escaping/flags, and end-to-end CLI behavior including AI-tag failure handling).
- Built and installed into a clean venv (`pip install .`); both console commands printed `prompt-tag-organizer 0.1.0`.
- Full manual workflow against a sample folder ran clean: `scan` → `tag` (frontmatter written) → `search` (typo matched) → `dupes` (2 flagged) → `export` (index.html with near-duplicate warnings and Asdale Dynamics credit).
- AI tagging verified against a mock OpenAI-compatible endpoint on an ephemeral port: dry-run suggestions and `--apply` correctly wrote Markdown frontmatter and merged tags into JSON; unreachable endpoints exit with code 2 and a clear message without touching files.
- Newly discovered robustness fix during verification: dropped/broken connections (`RemoteDisconnected`, non-JSON replies) are now caught and reported cleanly.

## Known gaps

- Frontmatter is a small practical YAML subset (inline lists, block lists, scalars) — not a full YAML parser; unusual quoting may round-trip imperfectly.
- Duplicate grouping compares each cluster seed to later items (single pass), so rare three-way clusters split by transitive distance are not merged.
- `pto ai-tag` calls each prompt once with no batching/concurrency, so large libraries with a slow local model can take a while.
- HTML index tags/scores are whatever files declare; there is no sorting or "best of" curation view yet.
- `--remove` on JSON files is not implemented (Markdown files only).
- No `--recursive false` / include-filter options; scans always recurse, skipping `.git`, `node_modules`, caches, and virtualenvs.
