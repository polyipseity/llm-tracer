"""Decision event logging for accepted/rejected/undecided chat review outcomes."""

from datetime import UTC, datetime

from llm_tracer.config import TracerConfig
from llm_tracer.storage import (
    list_jsonl_files,
    read_jsonl_records,
    write_partitioned_jsonl,
)
from llm_tracer.utils.hashing import hash_bytes

"""Public symbols exported by this module."""
__all__ = ("read_latest_decisions", "record_decision")


def _read_decision_rows(*, config: TracerConfig) -> list[dict[str, object]]:
    """Read all date-partitioned decision rows from private decision storage."""

    decisions_root = config.repo_dir / "data/decisions"
    rows: list[dict[str, object]] = []
    for file in list_jsonl_files(decisions_root):
        rows.extend(read_jsonl_records(file))
    rows.sort(key=lambda item: (str(item["timestamp"]), str(item["decision_event_id"])))
    return rows


def read_latest_decisions(*, config: TracerConfig) -> dict[str, str]:
    """Read latest decision per chat from date-partitioned decision JSONL files."""

    latest: dict[str, str] = {}
    for row in _read_decision_rows(config=config):
        chat_id = str(row["chat_id"])
        decision = str(row["decision"])
        latest[chat_id] = decision
    return latest


def record_decision(
    *,
    config: TracerConfig,
    chat_id: str,
    decision: str,
    reason: str | None,
) -> str:
    """Persist one latest decision event in date-partitioned JSONL storage.

    If a chat already has a stored decision, the previous row is replaced so
    each chat has at most one decision row in `data/decisions`.

    Returns the deterministic `decision_event_id` for the persisted event.
    """

    if decision not in {"accepted", "rejected", "undecided"}:
        raise ValueError("decision must be 'accepted', 'rejected', or 'undecided'")

    now = datetime.now(tz=UTC)
    payload = f"{chat_id}|{decision}|{reason or ''}|{now.isoformat()}"
    decision_event_id = hash_bytes(payload.encode("utf-8"))
    row: dict[str, object] = {
        "decision_event_id": decision_event_id,
        "chat_id": chat_id,
        "decision": decision,
        "timestamp": now.isoformat(),
        "reason": reason,
    }

    decisions_root = config.repo_dir / "data/decisions"
    existing_rows = [
        existing
        for existing in _read_decision_rows(config=config)
        if str(existing["chat_id"]) != chat_id
    ]
    existing_rows.append(row)
    existing_rows.sort(
        key=lambda item: (str(item["timestamp"]), str(item["decision_event_id"]))
    )

    write_partitioned_jsonl(
        decisions_root,
        existing_rows,
        max_bytes=config.chunk_size_bytes,
    )

    return decision_event_id
