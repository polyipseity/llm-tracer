"""Interactive chat review session for manual decision annotation."""

from datetime import UTC, date, datetime, time
from fnmatch import fnmatchcase

import typer

from llm_tracer.config import TracerConfig
from llm_tracer.decisions import record_decision
from llm_tracer.schema import ChatSession
from llm_tracer.storage import read_parquet_dataframe, read_private_chats

"""Public symbols exported by this module."""
__all__ = (
    "interactive_review",
    "select_review_sessions",
)

"""Mapping from single-character shortcut to decision value (None = no decision recorded)."""
_REVIEW_SHORTCUTS: dict[str, str | None] = {
    "a": "accepted",
    "r": "rejected",
    "u": "undecided",
    "s": None,
    "q": None,
}

"""Number of messages shown per chat in the interactive preview pane."""
_PREVIEW_MESSAGES = 5

"""Maximum character count for each message content preview."""
_PREVIEW_CONTENT_LEN = 200


def _parse_iso_date(raw: str) -> date:
    """Parse a `YYYY-MM-DD` date literal."""

    try:
        return date.fromisoformat(raw)
    except ValueError as error:
        raise ValueError(f"invalid date literal: {raw!r}") from error


def _parse_iso_datetime(raw: str) -> datetime:
    """Parse an ISO-8601 datetime and normalize to timezone-aware UTC."""

    normalized = raw.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError(f"invalid datetime literal: {raw!r}") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _build_datetime_bounds(
    *,
    on_date: str | None,
    from_date: str | None,
    to_date: str | None,
    at_datetime: str | None,
    from_datetime: str | None,
    to_datetime: str | None,
) -> tuple[datetime | None, datetime | None]:
    """Build inclusive UTC datetime bounds from review filter literals."""

    lower: datetime | None = None
    upper: datetime | None = None

    if on_date is not None:
        day = _parse_iso_date(on_date)
        lower = datetime.combine(day, time.min, tzinfo=UTC)
        upper = datetime.combine(day, time.max, tzinfo=UTC)

    if from_date is not None:
        day = _parse_iso_date(from_date)
        candidate = datetime.combine(day, time.min, tzinfo=UTC)
        lower = candidate if lower is None else max(lower, candidate)
    if to_date is not None:
        day = _parse_iso_date(to_date)
        candidate = datetime.combine(day, time.max, tzinfo=UTC)
        upper = candidate if upper is None else min(upper, candidate)

    if at_datetime is not None:
        exact = _parse_iso_datetime(at_datetime)
        lower = exact if lower is None else max(lower, exact)
        upper = exact if upper is None else min(upper, exact)
    if from_datetime is not None:
        candidate = _parse_iso_datetime(from_datetime)
        lower = candidate if lower is None else max(lower, candidate)
    if to_datetime is not None:
        candidate = _parse_iso_datetime(to_datetime)
        upper = candidate if upper is None else min(upper, candidate)

    if lower is not None and upper is not None and lower > upper:
        raise ValueError("invalid time filter: lower bound is after upper bound")
    return lower, upper


def _match_tag_parts(
    tag_parts: tuple[str, ...], pattern_parts: tuple[str, ...]
) -> bool:
    """Match slash-delimited tag parts against glob parts with `**` recursion."""

    if not pattern_parts:
        return not tag_parts
    head, *tail_list = pattern_parts
    tail = tuple(tail_list)
    if head == "**":
        if _match_tag_parts(tag_parts, tail):
            return True
        if not tag_parts:
            return False
        return _match_tag_parts(tag_parts[1:], pattern_parts)
    if not tag_parts:
        return False
    if not fnmatchcase(tag_parts[0], head):
        return False
    return _match_tag_parts(tag_parts[1:], tail)


def _tag_matches_pattern(tag: str, pattern: str) -> bool:
    """Return whether one normalized tag matches one slash-aware glob pattern."""

    tag_parts = tuple(part for part in tag.split("/") if part)
    pattern_parts = tuple(part for part in pattern.split("/") if part)
    return _match_tag_parts(tag_parts, pattern_parts)


def _session_matches_tag_patterns(
    session: ChatSession,
    tag_patterns: tuple[str, ...],
) -> bool:
    """Return whether a session matches all requested tag patterns."""

    if not tag_patterns:
        return True
    for pattern in tag_patterns:
        if not any(_tag_matches_pattern(tag, pattern) for tag in session.tags):
            return False
    return True


def select_review_sessions(
    sessions: dict[str, ChatSession],
    *,
    decided_chat_ids: set[str],
    on_date: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    at_datetime: str | None = None,
    from_datetime: str | None = None,
    to_datetime: str | None = None,
    tag_patterns: tuple[str, ...] = (),
) -> list[ChatSession]:
    """Select pending review sessions filtered by time bounds and tag globs."""

    lower, upper = _build_datetime_bounds(
        on_date=on_date,
        from_date=from_date,
        to_date=to_date,
        at_datetime=at_datetime,
        from_datetime=from_datetime,
        to_datetime=to_datetime,
    )

    selected: list[ChatSession] = []
    for chat_id, session in sorted(sessions.items()):
        if chat_id in decided_chat_ids:
            continue
        timestamp = session.timestamp.astimezone(UTC)
        if lower is not None and timestamp < lower:
            continue
        if upper is not None and timestamp > upper:
            continue
        if not _session_matches_tag_patterns(session, tag_patterns):
            continue
        selected.append(session)
    return selected


def _display_session(session: ChatSession) -> None:
    """Print a formatted chat session summary to the terminal."""

    typer.echo(f"\n{'=' * 60}")
    typer.echo(f"  id      : {session.id}")
    typer.echo(f"  source  : {session.source}")
    typer.echo(f"  model   : {session.model}")
    typer.echo(f"  ts      : {session.timestamp.isoformat()}")
    typer.echo(f"  tags    : {', '.join(session.tags) or '(none)'}")
    typer.echo(f"  msgs    : {len(session.messages)} total")
    typer.echo(f"{'=' * 60}")
    preview = session.messages[:_PREVIEW_MESSAGES]
    for msg in preview:
        content = msg.content[:_PREVIEW_CONTENT_LEN]
        if len(msg.content) > _PREVIEW_CONTENT_LEN:
            content += "…"
        typer.echo(f"  [{msg.role:>9}] {content}")
    if len(session.messages) > _PREVIEW_MESSAGES:
        typer.echo(f"  … {len(session.messages) - _PREVIEW_MESSAGES} more messages …")


def interactive_review(
    config: TracerConfig,
    *,
    on_date: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    at_datetime: str | None = None,
    from_datetime: str | None = None,
    to_datetime: str | None = None,
    tag_patterns: tuple[str, ...] = (),
) -> int:
    """Run an interactive review session for pending private chats.

    Chats that already have an explicit 'accepted' or 'rejected' decision are
    skipped; only undecided or unreviewed chats are presented.  Returns the
    number of decisions recorded during the session.
    """

    private_dir = config.repo_dir / "data/private/chats"
    sessions = read_private_chats(private_dir)

    decision_index_path = config.repo_dir / "data/indexes/decision_latest.parquet"
    decision_df = read_parquet_dataframe(decision_index_path)
    decided: set[str] = set()
    if (
        not decision_df.empty
        and "chat_id" in decision_df.columns
        and "decision" in decision_df.columns
    ):
        for _, row in decision_df.iterrows():
            if str(row["decision"]) in {"accepted", "rejected"}:
                decided.add(str(row["chat_id"]))

    pending = select_review_sessions(
        sessions,
        decided_chat_ids=decided,
        on_date=on_date,
        from_date=from_date,
        to_date=to_date,
        at_datetime=at_datetime,
        from_datetime=from_datetime,
        to_datetime=to_datetime,
        tag_patterns=tag_patterns,
    )
    if not pending:
        typer.echo("No chats pending review.")
        return 0

    typer.echo(f"{len(pending)} chat(s) pending review.")
    typer.echo("  a = accept   r = reject   u = undecided   s = skip   q = quit")

    recorded = 0
    for session in pending:
        _display_session(session)
        while True:
            raw = typer.prompt("  Decision", default="s").strip().lower()
            if raw not in _REVIEW_SHORTCUTS:
                typer.echo(f"  Unknown key {raw!r}. Use: a / r / u / s / q")
                continue
            if raw == "q":
                typer.echo("Review session ended.")
                return recorded
            decision = _REVIEW_SHORTCUTS[raw]
            if decision is not None:
                record_decision(
                    config=config,
                    chat_id=session.id,
                    decision=decision,
                    reason=None,
                )
                recorded += 1
                typer.echo(f"  Recorded: {decision}")
            break

    typer.echo(f"\nReview complete. Decisions recorded: {recorded}")
    return recorded
