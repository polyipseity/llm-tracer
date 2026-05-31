"""Shared test verification helpers for adapter example scripts."""

import json as _json
from collections.abc import Sequence
from pathlib import Path

from llm_tracer.schema import ChatSession

__all__ = ("verify_against_expected",)


"""Default fields ignored in fixture comparisons."""
_DEFAULT_SKIP_FIELDS: tuple[str, ...] = ("ingest_key",)


def verify_against_expected(
    sessions: list[ChatSession],
    expected_json_path: Path,
    *,
    skip_fields: Sequence[str] = _DEFAULT_SKIP_FIELDS,
) -> None:
    """Verify adapter output against an expected.json fixture.

    Pops specified fields (e.g., "ingest_key", "timestamp") from both
    actual and expected results before comparison.
    """
    _expected = _json.loads(expected_json_path.read_text(encoding="utf-8"))
    _actual = [s.model_dump(mode="json") for s in sessions]

    for _d in _actual + _expected:
        for field in skip_fields:
            _d.pop(field, None)

    assert _actual == _expected, "session output does not match expected.json"
