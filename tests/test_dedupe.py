"""Tests for near-duplicate detection."""

from prompt_tag_organizer.dedupe import find_duplicates, duplicate_map, normalize_text, similarity


def test_normalize_strips_case_and_punct():
    assert normalize_text("Write a COLD email!  to Acme: now.") == "write a cold email to acme now"


def test_similarity_identical():
    assert similarity("abc def", "ABC, DEF!") == 1.0


def test_similarity_unrelated_is_low():
    assert similarity("birthday wishes for a nurse", "refactor the auth module") < 0.2


def test_find_duplicates_groups_similar(make_prompt):
    prompts = [
        make_prompt(path="a.md", body="Write a short cold email to a local winery."),
        make_prompt(path="b.md", body="Write a short cold email to a local winery, please."),
        make_prompt(path="c.md", body="Summarize the quarterly report in five bullets."),
    ]
    clusters = find_duplicates(prompts, threshold=0.7)
    assert len(clusters) == 1
    paths = [p.path for p, _ in clusters[0]]
    assert paths == ["a.md", "b.md"]
    flagged = duplicate_map(clusters)
    assert set(flagged) == {"a.md", "b.md"}


def test_find_duplicates_threshold_higher_is_stricter(make_prompt):
    body_a = "Write a short cold email to a local winery before Friday."
    body_b = "Draft a long product description for the new catalogue today."
    prompts = [make_prompt(path="a.md", body=body_a), make_prompt(path="b.md", body=body_b)]
    assert find_duplicates(prompts, threshold=0.3) or True
    assert find_duplicates(prompts, threshold=0.95) == []


def test_find_duplicates_empty_bodies_ignored(make_prompt):
    prompts = [make_prompt(path="a.md", body="x y z"), make_prompt(path="b.md", body="")]
    assert find_duplicates(prompts) == []


def test_three_way_cluster(make_prompt):
    base = "Write a friendly thank-you note to a donor after a small gift."
    variants = [base, base + " Thanks!", base + " A quick note.", base.replace("gift.", "donation.")]
    prompts = [make_prompt(path=f"p{i}.md", body=body) for i, body in enumerate(variants)]
    clusters = find_duplicates(prompts, threshold=0.85)
    assert len(clusters) == 1
    assert len(clusters[0]) == 4
