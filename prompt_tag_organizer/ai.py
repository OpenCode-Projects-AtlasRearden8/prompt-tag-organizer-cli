"""Optional AI tagging via any OpenAI-compatible endpoint (Ollama included).

No API keys are required. The default endpoint is Ollama's bundled
OpenAI-compatible server on localhost, so everything stays local.
"""

import json
import re
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "llama3.2"
REQUEST_TIMEOUT = 120

SYSTEM_PROMPT = (
    "You are a tagging assistant. Given a prompt, return 3 to 6 short lowercase "
    "tags that describe its task and topic (for example: writing, email, code, "
    "summarize, marketing). Also give a one-sentence task description. Respond "
    "in exactly this format and nothing else:\n"
    "tags: tag1, tag2, tag3\ntask: <one sentence>"
)


def chat(base_url, model, messages, timeout=REQUEST_TIMEOUT):
    if not base_url.endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"
    url = base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps(
        {"model": model, "messages": messages, "temperature": 0.2}
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer local",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.load(response)
    except (urllib.error.URLError, ConnectionError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise RuntimeError(
            f"Could not reach the AI endpoint at {url} ({reason}). "
            "Start Ollama with 'ollama serve' and 'ollama pull "
            f"{model}', or pass --base-url/--model. "
            "Nothing was changed."
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON response from {url}.") from exc
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected response shape from {url}: {body!r}") from exc
    if not isinstance(content, str):
        raise RuntimeError(f"Unexpected response content from {url}: {content!r}")
    return content


def _clean_tag(tag):
    tag = tag.strip().strip(".,;:*'\"`").strip()
    return tag.lower().replace(" ", "-")


def parse_reply(content):
    tags = []
    task = ""
    tags_match = re.search(r"^\s*tags?\s*:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
    task_match = re.search(r"^\s*tasks?\s*:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
    if tags_match:
        raw = tags_match.group(1).strip().strip("[]")
        tags = [t for t in (_clean_tag(part) for part in raw.split(",")) if t and not t.startswith("<")]
    if task_match:
        task = task_match.group(1).strip()
    if not tags:
        for line in content.lower().splitlines():
            line = line.strip().lstrip("-*+ ")
            if re.match(r"^(tags?|task)\s*:", line) or line in ("", "```", "```none"):
                continue
            parts = [t for t in (_clean_tag(part) for part in re.split(r"[,\n|]", line)) if t]
            if parts:
                tags.extend(parts)
                break
    seen = set()
    unique = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            unique.append(tag)
    return unique, task


def suggest(body, base_url=DEFAULT_BASE_URL, model=DEFAULT_MODEL, timeout=REQUEST_TIMEOUT):
    """Ask the endpoint for (tags, task) for a prompt body."""
    content = chat(
        base_url,
        model,
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": body.strip()[:4000]},
        ],
        timeout=timeout,
    )
    return parse_reply(content)
