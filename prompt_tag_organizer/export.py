"""Export prompts to a self-contained, browsable HTML index."""

import html
from datetime import datetime, timezone

EXPORTED_BY = "prompt-tag-organizer"
CREDIT = "Asdale Dynamics, LLC"


def _clip(text, limit=240):
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def render_html(prompts, duplicate_map=None, title="Prompt Index", threshold=None):
    """Render a standalone HTML-file index for the given prompts."""
    duplicate_map = duplicate_map or {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = []
    parts.append(
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n"
        "<style>\n"
        ":root { color-scheme: light dark; }\n"
        "body { font-family: system-ui, -apple-system, 'Segoe UI', sans-serif; max-width: 960px;"
        " margin: 0 auto; padding: 1.5rem; line-height: 1.5; }\n"
        "h1 { margin-bottom: 0.25rem; }\n"
        ".sub { color: #666; margin-bottom: 1.5rem; }\n"
        ".filters { margin: 1rem 0 1.5rem; }\n"
        ".filters button { margin-right: 0.4rem; margin-bottom: 0.4rem; cursor: pointer; }\n"
        "article { border: 1px solid rgba(128,128,128,.35); border-radius: 8px;"
        " padding: 1rem 1.25rem; margin-bottom: 1.25rem; }\n"
        "article h2 { margin: 0 0 .35rem; font-size: 1.15rem; }\n"
        ".dupe { border-color: #d97706; background: rgba(217,119,6,.07); }\n"
        ".flag { color: #b45309; font-weight: 600; font-size: .85rem; }\n"
        "code, pre { font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }\n"
        "pre { background: rgba(128,128,128,.12); padding: .75rem; border-radius: 6px;"
        " overflow-x: auto; white-space: pre-wrap; }\n"
        ".meta { margin: .35rem 0 .75rem; color: #777; font-size: .9rem; }\n"
        ".tag { display: inline-block; background: rgba(59,130,246,.15); color: #1d4ed8;"
        " border-radius: 999px; padding: 0 .55rem; margin: 0 .3rem .3rem 0; font-size: .8rem; }\n"
        "footer { margin-top: 2rem; color: #888; font-size: .85rem; }\n"
        "a { color: inherit; }\n"
        "</style>\n</head>\n<body>\n"
    )
    parts.append(f"<h1>{html.escape(title)}</h1>")
    parts.append(
        f'<p class="sub">{len(prompts)} prompt'
        f"{'s' if len(prompts) != 1 else ''} &middot; generated {now}</p>"
    )
    all_tags = sorted({t for p in prompts for t in p.tags})
    if all_tags:
        parts.append('<div class="filters">')
        parts.append('<button type="button" onclick="showAll()">All</button>')
        for tag in all_tags:
            parts.append(
                f'<button type="button" onclick="filterTag({html.escape(tag, quote=True)!r})">'
                f"#{html.escape(tag)}</button>"
            )
        parts.append("</div>")
    parts.append("<main>")
    if not prompts:
        parts.append("<p>No prompts found. Add Markdown or JSON prompt files and rescan.</p>")
    prompt_id = 0
    for prompt in prompts:
        prompt_id += 1
        dupes = duplicate_map.get(prompt.path)
        dupe_class = " dupe" if dupes else ""
        parts.append(f'<article id="p{prompt_id}" class="prompt{dupe_class}" data-tags="{" ".join(prompt.tags)}">')
        parts.append(f"<h2>{html.escape(prompt.title or 'Untitled')}</h2>")
        flags = []
        if dupes:
            other = [p for p, _ in dupes if p.path != prompt.path]
            others = ", ".join(html.escape(p.path) for p in other) or "another prompt"
            flags.append(f'<span class="flag">&#9888; near-duplicate of {others}</span>')
        meta_bits = []
        source = prompt.path
        meta_bits.append(f"<code>{html.escape(source)}</code>")
        if prompt.meta.get("task"):
            meta_bits.append(f"task: {html.escape(str(prompt.meta['task']))}")
        if prompt.score is not None:
            meta_bits.append(f"score: {html.escape(str(prompt.score))}")
        parts.append(f'<p class="meta">{ " &middot; ".join(meta_bits) }</p>')
        if prompt.tags:
            tags_html = "".join(f'<span class="tag">#{html.escape(tag)}</span>' for tag in prompt.tags)
            parts.append(f"<p>{tags_html}</p>")
        for flag in flags:
            parts.append(f"<p>{flag}</p>")
        snippet = _clip(prompt.body)
        parts.append(f"<p>{html.escape(snippet)}</p>")
        if _clip(prompt.body) != " ".join(prompt.body.split()) or len(prompt.body) > 240:
            escaped_body = html.escape(prompt.body)
            parts.append(f"<details><summary>View full prompt</summary><pre>{escaped_body}</pre></details>")
        parts.append("</article>")
    parts.append("</main>")
    dup_count = len({p.path for cluster in duplicate_map.values() for p, _ in cluster}) if duplicate_map else 0
    parts.append(
        "<footer>Generated by <code>prompt-tag-organizer</code> "
        f"&middot; {dup_count} prompt(s) flagged as near-duplicates &middot; "
        f"Made by {CREDIT} &middot; MIT License</footer>"
    )
    parts.append(
        "<script>\n"
        "function showAll(){ document.querySelectorAll('article').forEach(el => el.style.display = ''); }\n"
        "function filterTag(tag){\n"
        "  document.querySelectorAll('article').forEach(el => {\n"
        "    var tags = (el.dataset.tags || '').split(/\\s+/);\n"
        "    el.style.display = tags.includes(tag) ? '' : 'none';\n"
        "  });\n"
        "}\n"
        "</script>\n"
        "</body>\n</html>\n"
    )
    return "\n".join(parts)


def export_index(prompts, out_path, duplicate_map=None, title="Prompt Index", threshold=None):
    from pathlib import Path

    html_text = render_html(prompts, duplicate_map=duplicate_map, title=title, threshold=threshold)
    Path(out_path).write_text(html_text, encoding="utf-8")
    return out_path
