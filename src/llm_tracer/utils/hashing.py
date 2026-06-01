"""Deterministic hashing helpers for identity and idempotency."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import blake3 as _blake3_mod

from llm_tracer.schema import ChatSession

"""Public symbols exported by this module."""
__all__ = (
    "compute_chat_id",
    "compute_content_hash",
    "compute_ingest_key",
    "hash_bytes",
)


def _normalize_timestamp(value: datetime) -> str:
    """Return a normalized UTC ISO8601 timestamp string for hashing."""

    return value.astimezone(UTC).isoformat()


def _stable_json_dumps(payload: dict[str, Any]) -> str:
    """Serialize a payload into deterministic JSON for hashing."""

    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def hash_bytes(value: bytes) -> str:
    """Return the BLAKE3 hex digest of a byte string."""

    return _blake3_mod.blake3(value).hexdigest()


def compute_chat_id(session: ChatSession) -> str:
    """Compute stable chat identity from (source, source_record_id).

    The returned hash is invariant under message additions for the same chat
    since it depends only on source + source_record_id, not on content.
    """
    identity = f"{session.source}|{session.source_record_id}"
    return hash_bytes(identity.encode("utf-8"))


def compute_ingest_key(*, source: str, source_record_id: str, source_path: Path) -> str:
    """Compute a deterministic ingest lineage key from source metadata."""

    payload = {
        "source": source,
        "source_record_id": source_record_id,
        "source_path": source_path.as_posix(),
    }
    return hash_bytes(_stable_json_dumps(payload).encode("utf-8"))


def compute_content_hash(session: ChatSession) -> str:
    """Compute deterministic content hash over sanitized session payload."""

    payload = {
        "chat_id": session.id,
        "source": session.source,
        "timestamp": _normalize_timestamp(session.timestamp),
        "model": session.model,
        "messages": [message.model_dump(mode="json") for message in session.messages],
        "tags": session.tags,
    }
    return hash_bytes(_stable_json_dumps(payload).encode("utf-8"))
