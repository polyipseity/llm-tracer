"""Decision event logging for accepted/rejected/undecided chat review outcomes."""

import json
from datetime import UTC, datetime

import pandas as pd

from llm_tracer.config import TracerConfig
from llm_tracer.storage import write_index_dataframe, write_partitioned_jsonl
from llm_tracer.utils.hashing import hash_bytes

"""Public symbols exported by this module."""
__all__ = ("record_decision",)


def record_decision(
    *,
    config: TracerConfig,
    chat_id: str,
    decision: str,
    reason: str | None,
) -> str:
    """Persist one decision event and refresh latest decision index.

    Returns the deterministic `decision_event_id` for the newly appended event.
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
    existing_rows: list[dict[str, object]] = []
    for file in (
        sorted(decisions_root.rglob("*.jsonl")) if decisions_root.exists() else []
    ):
        with file.open("r", encoding="utf-8") as handle:
            for line in handle:
                raw = line.strip()
                if raw:
                    existing_rows.append(json.loads(raw))
    existing_rows.append(row)
    existing_rows.sort(
        key=lambda item: (str(item["timestamp"]), str(item["decision_event_id"]))
    )

    write_partitioned_jsonl(
        decisions_root,
        existing_rows,
        max_bytes=config.chunk_size_bytes,
    )

    latest_index_path = config.repo_dir / "data/indexes/decision_latest.parquet"
    latest_df = pd.DataFrame(existing_rows)
    latest_df["timestamp"] = pd.to_datetime(latest_df["timestamp"], utc=True)
    latest_df = latest_df.sort_values("timestamp").drop_duplicates(
        subset=["chat_id"], keep="last"
    )
    latest_df["timestamp"] = latest_df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    write_index_dataframe(latest_index_path, latest_df)

    return decision_event_id
