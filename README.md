# prompt-tag-organizer

Organize your best prompts, locally — explained like a friend would.

`prompt-tag-organizer` is a small, zero-dependency Python CLI that keeps one tidy
library of the prompts you actually reuse. It scans your prompt folder
(Markdown and JSON), adds `tags` / `task` / `score` frontmatter, searches by tag
with fuzzy terms (typos welcome), flags near-duplicate prompts, and exports one
clean, browsable HTML index page. Everything stays on your machine.

## What it does

- **Scan** — finds `.md` and `.json` prompt files and shows their metadata.
- **Tag** — adds or updates `tags`, `task`, and `score` frontmatter in place.
- **Search** — fuzzy tag matching: `--tag emial` will still find `email`.
- **Dupes** — flags near-duplicate prompts so you keep one good version.
- **Export** — a single self-contained `index.html` with tag filter buttons,
  scores, task notes, full prompt text, and duplicate warnings.
- **AI tagging (optional)** — asks a local OpenAI-compatible endpoint
  (Ollama included, no API keys) to suggest tags and a one-line task.

No accounts, no network calls unless you opt into AI tagging, no secrets —
everything is plain files in your own folders.

## Install

Requires Python 3.9+. From this folder:

```bash
pip install .
```

This installs two commands: `prompt-tag-organizer` and the short form `pto`.

## Quick start

```bash
# see what is in your prompt folder
pto scan ~/prompts

# give one prompt tags, a task, and a score
pto tag ~/prompts/cold-email.md --tags email,marketing --task "write a cold email" --score 4
# merge extra tags into the existing ones instead of replacing
pto tag ~/prompts/cold-email.md --add-tags b2b

# search by tag, even with a typo
pto search ~/prompts --tag emial
pto search ~/prompts --tag email --strict

# near-duplicates (threshold is 0-1, higher = stricter)
pto dupes ~/prompts --threshold 0.85

# one clean browsable index page
pto export ~/prompts -o index.html

# optional AI tagging with Ollama (free, local, no keys)
ollama pull llama3.2
pto ai-tag ~/prompts            # suggestions only (dry run)
pto ai-tag ~/prompts --apply    # write suggestions into frontmatter
```

## Frontmatter format

Markdown prompt files use a small, human-friendly frontmatter block:

```markdown
---
tags: [email, marketing]
task: write a short cold email for a freelance service
score: 4
---

You are writing a cold email to a local winery...
```

JSON prompt files are either a single object, a list, or `{"group": [...]}`.
The prompt text lives under a key like `prompt`, `body`, `text`, `content`,
or `template`; other keys are kept as extra metadata.

## How the commands work

| Command | Purpose |
| --- | --- |
| `prompt-tag-organizer scan DIR [--json]` | List every prompt file with tags, task, score |
| `pto tag FILE [--tags ...] [--task ...] [--score N] [--dry-run]` | Add/update frontmatter |
| `pto search DIR --tag TERM [--strict]` | Fuzzy tag search |
| `pto dupes DIR [--threshold 0.9]` | Flag near-duplicates |
| `pto export DIR [-o index.html]` | Build the browsable HTML index |
| `pto ai-tag DIR [--base-url URL] [--model NAME] [--apply]` | Local-AI tagging |

**Custom endpoint:** any OpenAI-compatible server works, for example
`pto ai-tag ~/prompts --base-url http://localhost:1234/v1 --model qwen2-instruct`.
With Ollama, the default `--base-url http://localhost:11434/v1` needs nothing
beyond `ollama serve` and a pulled model — no API key, ever.

## Grading your library

Use `--score` as a simple 1–5 rating of how well a prompt performs for you.
The exported index sorts nothing for you on purpose — it shows everything,
with scores and tags, so you decide. Prune flagged near-duplicates and
low scorers; promote your favorites by giving them clear tags.

## Testing

```bash
pip install pytest   # or: python -m pip install pytest
python -m pytest
```

Tests cover frontmatter parsing and round-trips, fuzzy search, duplicate
detection, and the exported HTML index.

## Privacy

Your prompts and tags never leave your computer. The only optional network
call is the AI tagging step you point at an endpoint you choose — the
default is Ollama running on `localhost`. This project will never ask for
an API key or collect data.

## License

MIT License — Copyright (c) 2026 Asdale Dynamics, LLC. See [LICENSE](LICENSE).

Made by [Asdale Dynamics, LLC](https://dylanasdale.github.io) — beginner-friendly
AI tools in plain English.
