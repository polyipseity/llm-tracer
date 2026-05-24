"""OpenCode chat export adapter implementation."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from llm_tracer.adapters.base import BaseAdapter
from llm_tracer.core.schema import ChatSession

"""Public symbols exported by this module."""
__all__ = ("OpenCodeAdapter",)


class OpenCodeAdapter(BaseAdapter):
    """Normalize OpenCode chat exports into `ChatSession` records."""

    source_slug = "opencode"

    def default_roots(self, *, options: dict[str, str]) -> list[Path]:
        """Return default OpenCode export roots."""

        del options
        home = Path.home()
        return [
            home / ".opencode",
            home / "Library/Application Support/OpenCode",
        ]

    def ingest(self, root: Path, patterns: list[str]) -> list[ChatSession]:
        """Ingest and normalize OpenCode export files from a root directory."""

        sessions: list[ChatSession] = []
        for source_path in self.discover_files(root, patterns):
            for payload in self.parse_json_payloads(source_path):
                timestamp_raw = (
                    payload.get("createdAt")
                    or payload.get("created_at")
                    or payload.get("timestamp")
                )
                timestamp = _parse_timestamp(timestamp_raw)
                if timestamp is None:
                    continue
                messages = self.parse_messages(
                    payload.get("messages")
                    or payload.get("turns")
                    or payload.get("chat")
                    or payload.get("conversation")
                )
                if not messages:
                    continue
                model = str(
                    payload.get("model")
                    or payload.get("modelId")
                    or payload.get("assistant_model")
                    or "unknown"
                )
                source_record_id = str(
                    payload.get("id")
                    or payload.get("sessionId")
                    or payload.get("conversationId")
                    or payload.get("chatId")
                    or uuid4()
                )
                title = payload.get("title") or payload.get("name")
                tags_raw = payload.get("tags")
                tags = (
                    [str(tag) for tag in tags_raw] if isinstance(tags_raw, list) else []
                )
                sessions.append(
                    self.build_chat_session(
                        source_record_id=source_record_id,
                        source_path=source_path,
                        source_root=root,
                        timestamp=timestamp,
                        model=model,
                        messages=messages,
                        tags=tags,
                        title=str(title) if title is not None else None,
                    )
                )
        return sessions


def _parse_timestamp(value: object) -> datetime | None:
    """Parse potentially heterogeneous timestamp values into timezone-aware UTC."""

    if isinstance(value, datetime):
        return value.astimezone(UTC)
    if isinstance(value, str):
        cleaned = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(cleaned).astimezone(UTC)
        except ValueError:
            return None
    return None
