"""Unit tests for `llm_tracer.decisions`."""

from pathlib import Path

from llm_tracer.bootstrap import bootstrap_traces_repo
from llm_tracer.config import TracerConfig
from llm_tracer.decisions import read_latest_decisions, record_decision
from llm_tracer.storage import list_jsonl_files, read_jsonl_records

"""Public symbols exported by this test module (none)."""
__all__ = ()


def _read_decision_rows(repo_dir: Path) -> list[dict[str, object]]:
    """Read all persisted decision rows from partitioned JSONL files."""

    rows: list[dict[str, object]] = []
    for file in list_jsonl_files(repo_dir / "data/decisions"):
        rows.extend(read_jsonl_records(file))
    return rows


def test_record_decision_redecide_replaces_existing_chat_row(tmp_path: Path) -> None:
    """Re-deciding a chat should replace its prior decision row in JSONL storage."""

    repo_dir = tmp_path / "traces"
    bootstrap_traces_repo(repo_dir)
    config = TracerConfig(repo_dir=repo_dir)

    record_decision(
        config=config,
        chat_id="chat-1",
        decision="undecided",
        reason="first",
    )
    record_decision(
        config=config,
        chat_id="chat-1",
        decision="accepted",
        reason="final",
    )

    rows = [row for row in _read_decision_rows(repo_dir) if row["chat_id"] == "chat-1"]
    assert len(rows) == 1
    assert rows[0]["decision"] == "accepted"
    assert rows[0]["reason"] == "final"
    assert not (repo_dir / "data/indexes/decision_latest.parquet").exists()


def test_read_latest_decisions_returns_latest_map(tmp_path: Path) -> None:
    """Latest decision map should be sourced from date-partitioned decisions JSONL."""

    repo_dir = tmp_path / "traces"
    bootstrap_traces_repo(repo_dir)
    config = TracerConfig(repo_dir=repo_dir)

    record_decision(
        config=config,
        chat_id="chat-1",
        decision="accepted",
        reason=None,
    )
    record_decision(
        config=config,
        chat_id="chat-2",
        decision="rejected",
        reason=None,
    )
    record_decision(
        config=config,
        chat_id="chat-1",
        decision="undecided",
        reason="changed",
    )

    latest = read_latest_decisions(config=config)
    assert latest == {"chat-1": "undecided", "chat-2": "rejected"}
