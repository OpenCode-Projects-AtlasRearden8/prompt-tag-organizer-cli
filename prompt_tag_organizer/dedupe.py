"""Near-duplicate detection for prompt bodies."""

import difflib
import re


def normalize_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def token_set_similarity(a, b):
    tokens_a, tokens_b = set(a.split()), set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def similarity(a, b):
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    token = token_set_similarity(na, nb)
    if token < 0.15:
        return 0.0
    seq = difflib.SequenceMatcher(None, na, nb).ratio()
    return max(token, seq)


def find_duplicates(prompts, threshold=0.9):
    """Group prompts whose bodies are near-duplicates.

    Returns a list of clusters; each cluster is a list of (prompt, similarity)
    tuples with at least two members.
    """
    entries = [p for p in prompts if p.body.strip()]
    used = [False] * len(entries)
    clusters = []
    for i in range(len(entries)):
        if used[i]:
            continue
        cluster = [(entries[i], 1.0)]
        used[i] = True
        for j in range(i + 1, len(entries)):
            if used[j]:
                continue
            score = similarity(entries[i].body, entries[j].body)
            if score >= threshold:
                cluster.append((entries[j], score))
                used[j] = True
        if len(cluster) >= 2:
            clusters.append(cluster)
    return clusters


def duplicate_map(clusters):
    dupes = {}
    for cluster in clusters:
        for prompt, _score in cluster:
            dupes[prompt.path] = cluster
    return dupes
