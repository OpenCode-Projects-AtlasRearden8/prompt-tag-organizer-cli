"""Fuzzy tag search."""

import difflib


def collect_tags(prompts):
    tags = {}
    for prompt in prompts:
        for tag in prompt.tags:
            tags[tag] = tags.get(tag, 0) + 1
    return tags


def fuzzy_tags(query, available_tags, limit=5, cutoff=0.5):
    """Rank available tags against a (possibly misspelled) query."""
    query = query.strip().lower()
    if not query:
        return []
    available = sorted(set(available_tags))
    scored = []
    for tag in available:
        if tag == query:
            scored.append(tag)
        elif query in tag:
            scored.append(tag)
    matches = difflib.get_close_matches(query, available, n=limit * 2, cutoff=cutoff)
    for tag in matches:
        if tag not in scored:
            scored.append(tag)
    return scored[:limit]


def search_by_tag(prompts, query, strict=False, limit=5, cutoff=0.5):
    """Return (matched_query_tags, prompts) for a fuzzy or exact tag match."""
    available = collect_tags(prompts).keys()
    if strict:
        matched = [query.strip().lower()] if query.strip().lower() in available else []
    else:
        matched = fuzzy_tags(query, available, limit=limit, cutoff=cutoff)
    matched_set = set(matched)
    results = [
        prompt
        for prompt in prompts
        if matched_set.intersection(prompt.tags)
    ]
    return matched, results
