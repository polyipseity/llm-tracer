"""Interactive chat review session for manual decision annotation."""

import typer

from llm_tracer.config import TracerConfig
from llm_tracer.decisions import record_decision
from llm_tracer.schema import ChatSession
from llm_tracer.storage import read_parquet_dataframe, read_private_chats

"""Public symbols exported by this module."""
__all__ = ("interactive_review",)

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


def interactive_review(config: TracerConfig) -> int:
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

    pending = [s for cid, s in sorted(sessions.items()) if cid not in decided]
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
