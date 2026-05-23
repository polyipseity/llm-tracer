"""Deterministic hashing helpers for identity and idempotency."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from llm_tracer.core.schema import ChatSession, Message

"""Public symbols exported by this module."""
__all__ = (
    "canonical_chat_payload",
    "compute_chat_id",
    "compute_content_hash",
    "compute_ingest_key",
    "sha256_bytes",
)


def _normalize_timestamp(value: datetime) -> str:
    """Return a normalized UTC ISO8601 timestamp string for hashing."""

    return value.astimezone(UTC).isoformat()


def canonical_chat_payload(
    *,
    source: str,
    timestamp: datetime,
    model: str,
    messages: list[Message],
) -> dict[str, Any]:
    """Build the canonical payload used to derive stable chat identifiers."""

    return {
        "source": source,
        "timestamp": _normalize_timestamp(timestamp),
        "model": model,
        "messages": [
            {
                "role": message.role,
                "content": message.content,
                "tool_calls": message.tool_calls,
            }
            for message in messages
        ],
    }


def _stable_json_dumps(payload: dict[str, Any]) -> str:
    """Serialize a payload into deterministic JSON for hashing."""

    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def sha256_bytes(value: bytes) -> str:
    """Return the lowercase SHA256 hex digest of bytes."""

    return hashlib.sha256(value).hexdigest()


def compute_chat_id(session: ChatSession) -> str:
    """Compute deterministic chat identity from canonical session content."""

    payload = canonical_chat_payload(
        source=session.source,
        timestamp=session.timestamp,
        model=session.model,
        messages=session.messages,
    )
    return sha256_bytes(_stable_json_dumps(payload).encode("utf-8"))


def compute_ingest_key(*, source: str, source_record_id: str, source_path: Path) -> str:
    """Compute a deterministic ingest lineage key from source metadata."""

    payload = {
        "source": source,
        "source_record_id": source_record_id,
        "source_path": source_path.as_posix(),
    }
    return sha256_bytes(_stable_json_dumps(payload).encode("utf-8"))


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
    return sha256_bytes(_stable_json_dumps(payload).encode("utf-8"))
