"""Tests for fuzzy tag search."""

from prompt_tag_organizer.search import collect_tags, fuzzy_tags, search_by_tag


def _mk(make_prompt, path, tags):
    return make_prompt(path=path, meta={"tags": tags}, body=f"body for {tags}")


def test_collect_tags_counts(make_prompt):
    prompts = [_mk(make_prompt, "a.md", ["email"]), _mk(make_prompt, "b.md", ["email", "code"])]
    tags = collect_tags(prompts)
    assert tags == {"email": 2, "code": 1}


def test_fuzzy_matches_typo(make_prompt):
    tags = {"email", "writing", "code"}
    matched = fuzzy_tags("emial", tags)
    assert matched[0] == "email"


def test_fuzzy_substring_match(make_prompt):
    matched = fuzzy_tags("mail", ["email", "mailing-list", "code"], cutoff=0.5)
    assert "email" in matched


def test_fuzzy_no_garbage_matches(make_prompt):
    matched = fuzzy_tags("zzzzzz", ["email", "code"])
    assert matched == [] or "email" not in matched


def test_search_non_strict(make_prompt):
    prompts = [_mk(make_prompt, "a.md", ["email"]), _mk(make_prompt, "b.md", ["code"])]
    matched, results = search_by_tag(prompts, "emial")
    assert matched == ["email"]
    assert [p.path for p in results] == ["a.md"]


def test_search_strict(make_prompt):
    prompts = [_mk(make_prompt, "a.md", ["email"]), _mk(make_prompt, "b.md", ["code"])]
    matched, results = search_by_tag(prompts, "email", strict=True)
    assert matched == ["email"]
    assert len(results) == 1
    matched, results = search_by_tag(prompts, "emial", strict=True)
    assert matched == []
    assert results == []
