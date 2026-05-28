"""Unit tests for `llm_tracer.review`."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from llm_tracer.review import _display_session, select_review_sessions
from llm_tracer.schema import ChatSession, Message
from llm_tracer.storage import private_chat_path

"""Public symbols exported by this test module (none)."""
__all__ = ()


def _session(*, chat_id: str, timestamp: datetime, tags: list[str]) -> ChatSession:
    """Build a minimal review session fixture."""

    return ChatSession(
        id=chat_id,
        source="vscode",
        timestamp=timestamp,
        model="gpt-test",
        messages=[Message(role="user", content="hello", native_id=None)],
        tags=tags,
        source_record_id=chat_id,
        ingest_key="ingest-test-key",
    )


def test_select_review_sessions_filters_by_date_range() -> None:
    """Date range filters should include boundary days in UTC."""

    sessions = {
        "a": _session(
            chat_id="a",
            timestamp=datetime(2026, 5, 27, 23, 59, tzinfo=UTC),
            tags=["seed/demo"],
        ),
        "b": _session(
            chat_id="b",
            timestamp=datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
            tags=["seed/demo"],
        ),
        "c": _session(
            chat_id="c",
            timestamp=datetime(2026, 5, 29, 0, 0, tzinfo=UTC),
            tags=["seed/demo"],
        ),
    }

    selected = select_review_sessions(
        sessions,
        decided_chat_ids=set(),
        from_date="2026-05-28",
        to_date="2026-05-28",
    )

    assert [session.id for session in selected] == ["b"]


def test_select_review_sessions_filters_by_datetime_range() -> None:
    """Datetime range filters should include exact UTC boundary instants."""

    sessions = {
        "a": _session(
            chat_id="a",
            timestamp=datetime(2026, 5, 28, 10, 0, 0, tzinfo=UTC),
            tags=["seed/demo"],
        ),
        "b": _session(
            chat_id="b",
            timestamp=datetime(2026, 5, 28, 10, 0, 1, tzinfo=UTC),
            tags=["seed/demo"],
        ),
    }

    selected = select_review_sessions(
        sessions,
        decided_chat_ids=set(),
        from_datetime="2026-05-28T10:00:01Z",
        to_datetime="2026-05-28T10:00:01+00:00",
    )

    assert [session.id for session in selected] == ["b"]


def test_select_review_sessions_filters_by_exact_date() -> None:
    """Exact date selection should include all timestamps on that UTC day."""

    sessions = {
        "a": _session(
            chat_id="a",
            timestamp=datetime(2026, 5, 28, 0, 0, 0, tzinfo=UTC),
            tags=["seed/demo"],
        ),
        "b": _session(
            chat_id="b",
            timestamp=datetime(2026, 5, 28, 23, 59, 59, tzinfo=UTC),
            tags=["seed/demo"],
        ),
        "c": _session(
            chat_id="c",
            timestamp=datetime(2026, 5, 29, 0, 0, 0, tzinfo=UTC),
            tags=["seed/demo"],
        ),
    }

    selected = select_review_sessions(
        sessions,
        decided_chat_ids=set(),
        on_date="2026-05-28",
    )

    assert [session.id for session in selected] == ["a", "b"]


def test_select_review_sessions_filters_by_tag_globs() -> None:
    """Tag globs should support one-level and recursive matching patterns."""

    sessions = {
        "a": _session(
            chat_id="a",
            timestamp=datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
            tags=["import/id/vscode/session-a", "seed/demo"],
        ),
        "b": _session(
            chat_id="b",
            timestamp=datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
            tags=["import/id/lmstudio/session-b"],
        ),
    }

    selected_non_recursive = select_review_sessions(
        sessions,
        decided_chat_ids=set(),
        tag_patterns=("import/id/vscode/*",),
    )
    selected_recursive = select_review_sessions(
        sessions,
        decided_chat_ids=set(),
        tag_patterns=("import/**",),
    )

    assert [session.id for session in selected_non_recursive] == ["a"]
    assert [session.id for session in selected_recursive] == ["a", "b"]


def test_select_review_sessions_requires_all_tag_patterns() -> None:
    """Multiple tag patterns should apply with AND semantics."""

    sessions = {
        "a": _session(
            chat_id="a",
            timestamp=datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
            tags=["import/id/vscode/session-a", "seed/demo"],
        ),
        "b": _session(
            chat_id="b",
            timestamp=datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
            tags=["import/id/vscode/session-b"],
        ),
    }

    selected = select_review_sessions(
        sessions,
        decided_chat_ids=set(),
        tag_patterns=("import/id/vscode/*", "seed/*"),
    )

    assert [session.id for session in selected] == ["a"]


def test_select_review_sessions_excludes_decided() -> None:
    """Previously decided chats should be excluded from review selection."""

    sessions = {
        "a": _session(
            chat_id="a",
            timestamp=datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
            tags=["seed/demo"],
        ),
        "b": _session(
            chat_id="b",
            timestamp=datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
            tags=["seed/demo"],
        ),
    }

    selected = select_review_sessions(
        sessions,
        decided_chat_ids={"a"},
    )

    assert [session.id for session in selected] == ["b"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"on_date": "2026-99-99"},
        {"at_datetime": "not-a-datetime"},
        {
            "from_datetime": "2026-05-29T00:00:00Z",
            "to_datetime": "2026-05-28T00:00:00Z",
        },
    ],
)
def test_select_review_sessions_rejects_invalid_time_filters(
    kwargs: dict[str, object],
) -> None:
    """Invalid date/datetime literals and inverted ranges should raise errors."""

    sessions = {
        "a": _session(
            chat_id="a",
            timestamp=datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
            tags=["seed/demo"],
        )
    }

    with pytest.raises(ValueError):
        select_review_sessions(
            sessions,
            decided_chat_ids=set(),
            on_date=(
                str(kwargs["on_date"])
                if "on_date" in kwargs and kwargs["on_date"] is not None
                else None
            ),
            at_datetime=(
                str(kwargs["at_datetime"])
                if "at_datetime" in kwargs and kwargs["at_datetime"] is not None
                else None
            ),
            from_datetime=(
                str(kwargs["from_datetime"])
                if "from_datetime" in kwargs and kwargs["from_datetime"] is not None
                else None
            ),
            to_datetime=(
                str(kwargs["to_datetime"])
                if "to_datetime" in kwargs and kwargs["to_datetime"] is not None
                else None
            ),
        )


def test_display_session_prints_absolute_private_chat_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Review panel output should include absolute private chat JSON file path."""

    root = Path("/tmp/review-path-test")
    session = _session(
        chat_id="chat-path",
        timestamp=datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
        tags=["seed/demo"],
    )

    _display_session(session, private_chats_dir=root)

    output = capsys.readouterr().out
    expected_path = private_chat_path(root, session).resolve(strict=False)
    assert f"path    : {expected_path}" in output
