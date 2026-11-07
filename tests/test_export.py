"""Tests for the exported HTML index."""

import html as html_mod

from prompt_tag_organizer.dedupe import duplicate_map, find_duplicates
from prompt_tag_organizer.export import _clip, export_index, render_html


def _mk(make_prompt, path, body, tags=(), task=None, score=3):
    meta = {"tags": list(tags)}
    if task:
        meta["task"] = task
    meta["score"] = score
    return make_prompt(path=path, body=body, meta=meta)


def test_clip_truncates():
    assert _clip("a" * 400, limit=100).endswith("…")
    assert len(_clip("a" * 400, limit=100)) == 100


def test_render_html_contains_escape_and_text(make_prompt):
    prompt = _mk(make_prompt, "a.md", "Say <script>alert(1)</script> & bye", tags=["code"])
    page = render_html([prompt], title="Test Index")
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page
    assert "Test Index" in page
    assert "Asdale Dynamics, LLC" in page


def test_render_html_lists_tags_task_score(make_prompt):
    prompt = _mk(make_prompt, "a.md", "Body", tags=["email", "busywork"], task="send a note", score=5)
    page = render_html([prompt])
    assert "#email" in page and "#busywork" in page
    assert "send a note" in page
    assert "score: 5" in page


def test_render_html_flags_duplicates(make_prompt):
    d = find_duplicates(
        [
            _mk(make_prompt, "a.md", "alpha body text", tags=["x"]),
            _mk(make_prompt, "b.md", "alpha body text!", tags=["x"]),
        ],
        threshold=0.8,
    )
    flagged = duplicate_map(d)
    page = render_html(
        [
            _mk(make_prompt, "a.md", "alpha body text", tags=["x"]),
            _mk(make_prompt, "b.md", "alpha body text!", tags=["x"]),
        ],
        duplicate_map=flagged,
    )
    assert page.count("near-duplicate of") == 2


def test_render_html_empty_prompts(make_prompt):
    page = render_html([], title="Nothing")
    assert "No prompts found" in page


def test_render_html_filter_script_every_tag(make_prompt):
    page = render_html([_mk(make_prompt, "a.md", "B", tags=["one tag"])])
    assert "function filterTag" in page
    assert "data-tags" in page


def test_export_index_writes_file(tmp_path, make_prompt):
    out = tmp_path / "index.html"
    prompts = [_mk(make_prompt, "a.md", "body", tags=["t"])]
    written = export_index(prompts, out, title="Prompt Index")
    assert str(written) == str(out)
    text = out.read_text(encoding="utf-8")
    assert text.startswith("<!DOCTYPE html>")
    assert html_mod.unescape("Prompt Index") in text
