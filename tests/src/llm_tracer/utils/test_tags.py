"""Tests for hierarchical tag normalization and validation."""

import pytest

from llm_tracer.utils.tags import normalize_tag, normalize_tags

"""Public symbols exported by this test module (none)."""
__all__ = ()


def test_normalize_tag_roundtrip() -> None:
    """Normalization should preserve valid hierarchical tag values."""

    assert normalize_tag("import/some/folder") == "import/some/folder"


def test_normalize_tag_rejects_empty_component() -> None:
    """Tag normalization should reject empty path components."""

    with pytest.raises(ValueError):
        normalize_tag("import//folder")


def test_normalize_tags_deduplicates_and_sorts() -> None:
    """Tag list normalization should deduplicate and sort deterministically."""

    assert normalize_tags(["b/x", "a/x", "b/x"]) == ["a/x", "b/x"]
