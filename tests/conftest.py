"""Shared pytest fixtures."""

import pytest

from prompt_tag_organizer.parser import Prompt


@pytest.fixture
def make_prompt():
    def _make(path="p.md", fmt="md", title="T", meta=None, body="body text"):
        return Prompt(path=path, fmt=fmt, title=title, meta=meta or {}, body=body)

    return _make
