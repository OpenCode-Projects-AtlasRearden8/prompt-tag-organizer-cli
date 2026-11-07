"""End-to-end CLI tests using the console runner."""

import json
import sys

import pytest

from prompt_tag_organizer.cli import main


@pytest.fixture
def prompt_dir(tmp_path):
    d = tmp_path / "prompts"
    d.mkdir()
    (d / "cold-email.md").write_text(
        "---\ntags: [email, marketing]\ntask: cold email\nscore: 4\n---\nWrite a short cold email to a local winery.\n",
        encoding="utf-8",
    )
    (d / "cold-email-copy.md").write_text(
        "Write a short cold email to a local winery, this time!\n",
        encoding="utf-8",
    )
    (d / "list.json").write_text(
        json.dumps([{"prompt": "Summarize this article.", "tags": ["summarize"]}, {"prompt": "Fix my code."}]),
        encoding="utf-8",
    )
    return d


def run(*argv):
    return main(list(argv))


def test_scan_lists_files(prompt_dir, capsys):
    run("scan", str(prompt_dir))
    out = capsys.readouterr().out
    assert "cold-email.md" in out
    assert "list.json" in out
    assert "#email" in out


def test_scan_json_output(prompt_dir, capsys):
    run("scan", str(prompt_dir), "--json")
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 4
    assert any(entry["tags"] == ["email", "marketing"] for entry in data)


def test_tag_writes_frontmatter(prompt_dir):
    target = prompt_dir / "untagged.md"
    target.write_text("Plain body prompt.\n", encoding="utf-8")
    run("tag", str(target), "--tags", "misc", "--task", "file later", "--score", "2")
    text = target.read_text(encoding="utf-8")
    assert text.startswith("---\ntags: [misc]\ntask: file later\nscore: 2\n---")
    back = json.loads(run_scan_json(str(prompt_dir)))
    assert any(e["tags"] == ["misc"] for e in back)


def run_scan_json(directory):
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        run("scan", str(directory), "--json")
    return buf.getvalue()


def test_tag_add_tags_merges(prompt_dir):
    run("tag", str(prompt_dir / "cold-email.md"), "--add-tags", "outreach")
    text = (prompt_dir / "cold-email.md").read_text(encoding="utf-8")
    assert "tags: [email, marketing, outreach]" in text


def test_tag_dry_run_does_not_write(prompt_dir):
    target = prompt_dir / "cold-email.md"
    before = target.read_text(encoding="utf-8")
    run("tag", str(target), "--tags", "changed", "--dry-run")
    assert target.read_text(encoding="utf-8") == before


def test_search_fuzzy_finds_typo(prompt_dir, capsys):
    run("search", str(prompt_dir), "--tag", "emial")
    out = capsys.readouterr().out
    assert "#email" in out
    assert "cold-email.md" in out


def test_search_strict_miss_returns_empty(prompt_dir, capsys):
    code = run("search", str(prompt_dir), "--tag", "emial", "--strict")
    out = capsys.readouterr().out
    assert code == 0
    assert "No tag close to" in out


def test_dupes_flags_copy(prompt_dir, capsys):
    code = run("dupes", str(prompt_dir), "--threshold", "0.75")
    out = capsys.readouterr().out
    assert code in (0,)
    assert "cold-email-copy.md" in out and "cluster" in out.lower()


def test_export_writes_index_with_flags(prompt_dir):
    out_file = prompt_dir / "index.html"
    run("export", str(prompt_dir), "-o", str(out_file), "--threshold", "0.75")
    page = out_file.read_text(encoding="utf-8")
    assert page.startswith("<!DOCTYPE html>")
    assert "cold-email.md" in page
    assert "near-duplicate of" in page
    assert "Asdale Dynamics, LLC" in page


def test_ai_tag_fails_cleanly_when_no_server(prompt_dir, capsys, monkeypatch):
    monkeypatch.setattr("prompt_tag_organizer.ai.DEFAULT_BASE_URL", "http://127.0.0.1:9/v1")
    code = run("ai-tag", str(prompt_dir), "--base-url", "http://127.0.0.1:9/v1")
    err = capsys.readouterr().err
    assert code == 2
    assert "Could not reach the AI endpoint" in err


def test_version(capsys):
    with pytest.raises(SystemExit):
        run("--version")
    assert "prompt-tag-organizer" in capsys.readouterr().out
