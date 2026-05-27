"""Claude Code transcript adapter implementation.

Claude Code persists project transcripts as JSONL under
`~/.claude/projects/<project>/<session>.jsonl`.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from llm_tracer.adapters.base import BaseAdapter
from llm_tracer.adapters.claude_code.raw import ClaudeCodeEvent
from llm_tracer.schema.v1 import ChatSessionV1

"""Public symbols exported by this module."""
__all__ = ("ClaudeCodeAdapter",)


class ClaudeCodeAdapter(BaseAdapter):
    """Normalize Claude Code JSONL transcripts into ``ChatSessionV1`` records."""

    source_slug = "claude_code"

    def default_roots(self, *, options: dict[str, str]) -> list[Path]:
        """Return default Claude project transcript roots."""

        del options
        return [Path.home() / ".claude" / "projects"]

    def ingest(self, root: Path, patterns: list[str]) -> list[ChatSessionV1]:
        """Ingest Claude transcript JSONL files from one root directory."""

        sessions: list[ChatSessionV1] = []
        for source_path in self.discover_files(root, patterns):
            if source_path.suffix.lower() != ".jsonl":
                continue
            payloads = [
                cast("ClaudeCodeEvent", payload)
                for payload in self.parse_json_payloads(source_path)
            ]
            session = _ingest_transcript(self, payloads, source_path, root)
            if session is not None:
                sessions.append(session)
        return sessions


def _parse_timestamp(value: object) -> datetime | None:
    """Parse an ISO-8601 timestamp string into UTC."""

    if not isinstance(value, str):
        return None
    cleaned = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned).astimezone(UTC)
    except ValueError:
        return None


def _extract_text(content: object) -> str:
    """Extract text from Claude message content payloads."""

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


def _ingest_transcript(
    adapter: ClaudeCodeAdapter,
    payloads: list[ClaudeCodeEvent],
    source_path: Path,
    root: Path,
) -> ChatSessionV1 | None:
    """Convert one Claude transcript file into one normalized chat session."""

    if not payloads:
        return None

    messages: list[dict[str, Any]] = []
    model = "unknown"
    timestamp = datetime.fromtimestamp(source_path.stat().st_mtime, tz=UTC)
    session_id = source_path.stem

    for payload in payloads:
        if payload.get("sessionId"):
            session_id = str(payload["sessionId"])
        parsed_timestamp = _parse_timestamp(payload.get("timestamp"))
        if parsed_timestamp is not None:
            timestamp = min(timestamp, parsed_timestamp)

        event_type = payload.get("type")
        if event_type not in {"user", "assistant", "system", "tool"}:
            continue
        message_obj = payload.get("message")
        if not isinstance(message_obj, dict):
            continue
        message = cast("dict[str, Any]", message_obj)
        role = str(message.get("role") or event_type)
        text = _extract_text(message.get("content"))
        if not text:
            continue
        native_id = payload.get("uuid") or message.get("id")
        if model == "unknown" and message.get("model") is not None:
            model = str(message.get("model"))
        messages.append(
            {
                "role": role,
                "content": text,
                "native_id": str(native_id) if native_id is not None else None,
            }
        )

    parsed_messages = adapter.parse_messages(messages)
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
    )
