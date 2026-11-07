"""Tests for frontmatter parsing, writing, and prompt loading."""

import json

import pytest

from prompt_tag_organizer.parser import (
    DEFAULT_EXTENSIONS,
    Prompt,
    apply_frontmatter,
    format_meta,
    load_json_file,
    load_prompt_file,
    parse_frontmatter,
    scan_directory,
    write_frontmatter,
)


def test_parse_frontmatter_inline_list_and_scalars():
    text = "---\ntags: [email, marketing]\ntask: write a cold email\nscore: 4\n---\nBody line.\n"
    meta, body, had = parse_frontmatter(text)
    assert had is True
    assert meta["tags"] == ["email", "marketing"]
    assert meta["task"] == "write a cold email"
    assert meta["score"] == 4
    assert body == "Body line.\n"


def test_parse_frontmatter_block_list():
    text = "---\ntags:\n  - writing\n  - email\n---\nX"
    meta, body, had = parse_frontmatter(text)
    assert had is True
    assert meta["tags"] == ["writing", "email"]


def test_parse_no_frontmatter():
    meta, body, had = parse_frontmatter("# Just a heading\n")
    assert (meta, body, had) == ({}, "# Just a heading\n", False)


def test_parse_frontmatter_missing_close():
    meta, body, had = parse_frontmatter("---\ntags: [a]\nnever closed\n")
    assert had is False
    assert meta == {}
    assert "never closed" in body


def test_write_frontmatter_round_trip():
    meta = {"tags": ["code", "python"], "task": "explain imports", "score": 3.5}
    body = "Body.\n"
    content, had = write_frontmatter(meta, body)
    assert had is True
    back, body_back, had_back = parse_frontmatter(content)
    assert had_back is True
    assert back == meta
    assert body_back == body


def test_write_frontmatter_quotes_colon_in_task():
    content, _ = write_frontmatter({"task": "write: email"}, "B\n")
    back, _, _ = parse_frontmatter(content)
    assert back["task"] == "write: email"


def test_write_frontmatter_empty_meta_drops_block():
    content, had = write_frontmatter({}, "B\n")
    assert had is False
    assert content == "B\n"


def test_format_meta_orders_tags_task_score_first():
    rendered = format_meta({"score": 2, "title": "T", "task": "t", "tags": ["a"], "note": "n"})
    keys = [line.split(":")[0] for line in rendered.splitlines()]
    assert keys[0] == "tags"
    assert keys[1] == "task"
    assert keys[2] == "score"


def test_load_markdown_file(tmp_path):
    md = tmp_path / "cold-email.md"
    md.write_text(
        "---\ntags: [email]\ntask: cold email\nscore: 4\n---\n# Cold Email\nBody text\n",
        encoding="utf-8",
    )
    prompt = load_prompt_file(md)[0]
    assert prompt.fmt == "md"
    assert prompt.title == "Cold Email"
    assert prompt.tags == ["email"]
    assert prompt.score == 4


def test_load_json_single_object(tmp_path):
    fp = tmp_path / "one.json"
    fp.write_text(
        json.dumps({"prompt": "Sum this article.", "tags": ["summarize"], "score": 3}),
        encoding="utf-8",
    )
    prompt = load_prompt_file(fp)[0]
    assert prompt.body == "Sum this article."
    assert prompt.tags == ["summarize"]
    assert prompt.score == 3


def test_load_json_list_gets_index_paths(tmp_path):
    fp = tmp_path / "many.json"
    fp.write_text(
        json.dumps([{"prompt": "A"}, {"prompt": "B", "tags": ["t"]}]),
        encoding="utf-8",
    )
    prompts = load_json_file(fp)
    assert len(prompts) == 2
    assert prompts[0].path == f"{fp}[0]"
    assert prompts[1].tags == ["t"]


def test_load_json_grouped(tmp_path):
    fp = tmp_path / "groups.json"
    fp.write_text(
        json.dumps({"work": [{"prompt": "A", "task": "do"}]}),
        encoding="utf-8",
    )
    prompts = load_json_file(fp)
    assert prompts[0].meta["group"] == "work"
    assert prompts[0].meta["task"] == "do"


def test_load_json_bad_type_raises(tmp_path):
    fp = tmp_path / "bad.json"
    fp.write_text('"just a string"', encoding="utf-8")
    with pytest.raises(ValueError):
        load_json_file(fp)


def test_scan_directory_finds_md_and_json(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.md").write_text("Prompt A\n", encoding="utf-8")
    (tmp_path / "sub" / "b.json").write_text(json.dumps({"prompt": "B"}), encoding="utf-8")
    (tmp_path / "ignore.txt").write_text("not a prompt", encoding="utf-8")
    prompts = scan_directory(tmp_path, extensions=DEFAULT_EXTENSIONS)
    paths = {p.path for p in prompts}
    assert tmp_path.joinpath("a.md").as_posix() in str(paths) or any("a.md" in p for p in paths)
    assert len(prompts) == 2
    assert not any(p.path.endswith("ignore.txt") for p in prompts)


def test_scan_directory_skips_git(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "c.md").write_text("hidden\n", encoding="utf-8")
    prompts = scan_directory(tmp_path)
    assert prompts == []
