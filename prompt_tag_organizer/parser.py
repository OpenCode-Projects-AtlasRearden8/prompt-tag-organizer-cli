"""Loading, parsing, and frontmatter handling for prompt files."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_EXTENSIONS = (".md", ".json")
DEFAULT_SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
}

META_ORDER = ("tags", "task", "score")


@dataclass
class Prompt:
    path: str
    fmt: str  # "md" or "json"
    title: str
    meta: dict = field(default_factory=dict)
    body: str = ""

    @property
    def tags(self):
        tags = self.meta.get("tags") or []
        return [str(t).lower() for t in tags]

    @property
    def score(self):
        return self.meta.get("score")


def convert_scalar(value):
    if not isinstance(value, str):
        return value
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    low = text.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("null", "none", "~", ""):
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def _split_inline_list(text):
    inner = text.strip()[1:-1]
    if not inner.strip():
        return []
    items = []
    for part in re.split(r",(?=(?:[^\"']*[^\"'])*$)", inner):
        item = convert_scalar(part.strip())
        if item not in (None, ""):
            items.append(item)
    return items


def _parse_list_block(lines, start):
    items = []
    i = start
    while i < len(lines):
        m = re.match(r"^\s+-\s*(.*)$", lines[i])
        if not m:
            break
        items.append(convert_scalar(m.group(1)))
        i += 1
    return items, i


def parse_frontmatter(text):
    """Return (meta, body, had_frontmatter) for a markdown-style document."""
    meta = {}
    body = text
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return meta, text, False
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            end = i
            break
    if end is None:
        return meta, text, False
    i = 1
    while i < end:
        line = lines[i]
        m = re.match(r"^([A-Za-z0-9_.\- ]+?)\s*:\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key = m.group(1).strip()
        value = m.group(2).strip()
        if not value:
            sub, consumed = _parse_list_block(lines, i + 1)
            if consumed > i + 1 or (consumed == i + 1 and consumed <= end):
                if sub:
                    meta[key] = sub
                    i = consumed
                    continue
            meta[key] = None
        elif value.startswith("[") and value.endswith("]"):
            meta[key] = _split_inline_list(value)
        else:
            meta[key] = convert_scalar(value)
        i += 1
    body = "\n".join(lines[end + 1 :])
    if body and text.endswith("\n"):
        body += "\n"
    return meta, body, True


def format_scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "" or re.match(r'^[-?#\[\]{}|>&*!%@`"\'\s]', text) or ": " in text or text.endswith(":"):
        escaped = text.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    return text


def format_meta(meta):
    lines = []
    for key in META_ORDER:
        if key in meta:
            lines.append(f"{key}: {format_value(meta[key])}")
    for key, value in meta.items():
        if key not in META_ORDER:
            lines.append(f"{key}: {format_value(value)}")
    return "\n".join(lines)


def format_value(value):
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(format_scalar(v) for v in value) + "]"
    return format_scalar(value)


def write_frontmatter(meta, body):
    """Return (content, had_frontmatter) with meta rendered above body."""
    rendered = format_meta(meta)
    if not rendered:
        content = body
        return content, False
    content = "---\n" + rendered + "\n---\n" + body.lstrip("\n")
    if not content.endswith("\n"):
        content += "\n"
    return content, True


def _extract_title_md(body, path):
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped in ("---", "..."):
            continue
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or Path(path).stem
        return stripped[:80]
    return Path(path).stem


PROMPT_TEXT_KEYS = ("prompt", "template", "body", "text", "content", "message")


def _split_json_object(obj, index, path):
    """Return (meta, body, title_hint) treating known text keys as the body."""
    if not isinstance(obj, dict):
        return {}, "", ""
    meta = {}
    body = ""
    title = ""
    for key, value in obj.items():
        if key.lower() in PROMPT_TEXT_KEYS and isinstance(value, str):
            body = value
            continue
        if key.lower() == "title" and isinstance(value, str):
            title = value
            continue
        meta[key] = value
    if not body and "input" in obj and isinstance(obj["input"], str):
        body = obj["input"]
    if index is not None:
        meta["$index"] = index
    return meta, body, title


def load_json_file(path):
    prompts = []
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, list):
        for idx, obj in enumerate(data):
            meta, body, title = _split_json_object(obj, idx, path)
            prompts.append(Prompt(path=f"{path}[{idx}]", fmt="json", title=title or "", meta=meta, body=body))
    elif isinstance(data, dict):
        if any(isinstance(v, list) and v and isinstance(v[0], dict) for v in data.values()):
            for key, value in data.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    for idx, obj in enumerate(value):
                        meta, body, title = _split_json_object(obj, idx, path)
                        meta.setdefault("group", key)
                        prompts.append(Prompt(path=f"{path}#{key}[{idx}]", fmt="json", title=title or "", meta=meta, body=body))
        else:
            meta, body, title = _split_json_object(data, None, path)
            prompts.append(Prompt(path=str(path), fmt="json", title=title or "", meta=meta, body=body))
    else:
        raise json.JSONDecodeError("expected an object or list of objects", "", 0)
    for p in prompts:
        if not p.title:
            p.title = _extract_title_md(p.body, p.path)
    return prompts


def apply_frontmatter(file_path, prompt, meta):
    """Return (content, had_frontmatter) with new meta merged onto a prompt."""
    return write_frontmatter(meta, prompt.body)


def load_markdown_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    meta, body, _ = parse_frontmatter(text)
    title = _extract_title_md(body, str(path))
    return Prompt(path=str(path), fmt="md", title=str(meta.get("title") or title), meta=meta, body=body)


def load_prompt_file(path):
    path = str(path)
    if path.lower().endswith(".json"):
        items = load_json_file(path)
        return items
    prompt = load_markdown_file(path)
    prompt.title = str(prompt.meta.get("title") or prompt.title)
    return [prompt]


def scan_directory(directory, extensions=DEFAULT_EXTENSIONS, skip_dirs=None, recursive=True):
    skip = set(skip_dirs or DEFAULT_SKIP_DIRS)
    root = Path(directory)
    prompts = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in skip for part in path.parts):
            continue
        if path.suffix.lower() not in extensions:
            continue
        try:
            prompts.extend(load_prompt_file(path))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return prompts
