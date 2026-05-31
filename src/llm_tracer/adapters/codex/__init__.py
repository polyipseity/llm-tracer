"""Codex rollout adapter implementation.

Codex stores local sessions as JSONL rollout files under
`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from llm_tracer.adapters.base import BaseAdapter
from llm_tracer.adapters.codex.raw import CodexEvent
from llm_tracer.schema import AttachmentPolicy
from llm_tracer.schema.v1 import ChatSessionV1

"""Public symbols exported by this module."""
__all__ = ("CodexAdapter",)


class CodexAdapter(BaseAdapter):
    """Normalize Codex rollout JSONL files into ``ChatSessionV1`` records."""

    source_slug = "codex"

    def default_roots(self, *, options: dict[str, str]) -> list[Path]:
        """Return default Codex rollout roots."""

        del options
        return [Path.home() / ".codex" / "sessions"]

    def ingest(self, root: Path, patterns: list[str]) -> list[ChatSessionV1]:
        """Ingest Codex rollout JSONL files from one root directory."""

        sessions: list[ChatSessionV1] = []
        for source_path in self.discover_files(root, patterns):
            if source_path.suffix.lower() != ".jsonl":
                continue
            payloads = [
                cast("CodexEvent", payload)
                for payload in self.parse_json_payloads(source_path)
            ]
            session = _ingest_rollout(self, payloads, source_path, root)
            if session is not None:
                sessions.append(session)
        return sessions


def _parse_timestamp(value: object) -> datetime | None:
    """Parse an ISO-8601 timestamp string into UTC."""

    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value).astimezone(UTC)
    except ValueError:
        return None


def _extract_text(content: object) -> str:
    """Extract text from Codex message content payloads."""

    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        part = cast("dict[str, Any]", item)
        if part.get("type") != "text":
            continue
        text = part.get("text")
        if text is None:
            continue
        text_str = str(text).strip()
        if text_str:
            parts.append(text_str)
    return "\n".join(parts).strip()


def _ingest_rollout(
    adapter: CodexAdapter,
    payloads: list[CodexEvent],
    source_path: Path,
    root: Path,
) -> ChatSessionV1 | None:
    """Convert one Codex rollout file into one normalized chat session."""

    if not payloads:
        return None

    timestamp = datetime.fromtimestamp(source_path.stat().st_mtime, tz=UTC)
    session_id = source_path.stem
    model = "unknown"
    messages: list[dict[str, Any]] = []

    for payload in payloads:
        payload_type = payload.get("type")
        parsed_timestamp = _parse_timestamp(payload.get("timestamp"))
        if parsed_timestamp is not None:
            timestamp = min(timestamp, parsed_timestamp)

        if payload_type == "session" and payload.get("id") is not None:
            session_id = str(payload["id"])
            continue
        if payload_type == "model_change" and payload.get("modelId") is not None:
            model = str(payload["modelId"])
            continue
        if payload_type != "message":
            continue

        message_obj = payload.get("message")
        if not isinstance(message_obj, dict):
            continue
        message = cast("dict[str, Any]", message_obj)
        role = str(message.get("role") or "assistant")
        text = _extract_text(message.get("content"))
        if not text:
            continue
        native_id = payload.get("id")
        if model == "unknown" and message.get("model") is not None:
            model = str(message.get("model"))
        messages.append(
            {
                "role": role,
                "content": text,
                "native_id": str(native_id) if native_id is not None else None,
                "timestamp": payload.get("timestamp"),
                "model": message.get("model"),
            }
        )

    parsed_messages = adapter.parse_messages(
        messages,
        attachment_policy=AttachmentPolicy.METADATA_ONLY,
    )
    if not parsed_messages:
        return None

    folder = source_path.parent.name if source_path.parent != root else None
    return adapter.build_chat_session(  # type: ignore[return-value]
        source_record_id=session_id,
        source_path=source_path,
        source_root=root,
        timestamp=timestamp,
        model=model,
        messages=parsed_messages,
        tags=[],
        title=None,
        folder=folder,
        attachment_policy=AttachmentPolicy.METADATA_ONLY,
    )
