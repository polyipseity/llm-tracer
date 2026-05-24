"""PI agent trace adapter implementation.

Note: Storage paths and trace format are speculative — no public documentation
was found for PI Coding Agent's data storage format.  The default roots and
field names were inferred by reverse-engineering locally captured traces.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from llm_tracer.adapters.base import BaseAdapter
from llm_tracer.core.schema import ChatSession

"""Public symbols exported by this module."""
__all__ = ("PiCodingAgentAdapter",)


class PiCodingAgentAdapter(BaseAdapter):
    """Normalize PI-agent execution traces into `ChatSession` records."""

    source_slug = "pi_coding_agent"

    def default_roots(self, *, options: dict[str, str]) -> list[Path]:
        """Return default PI coding agent trace directories."""

        del options
        home = Path.home()
        return [
            home / ".pi-agent",
            home / "Library/Application Support/PiAgent",
        ]

    def ingest(self, root: Path, patterns: list[str]) -> list[ChatSession]:
        """Ingest and normalize PI-agent trace files from a root directory."""

        sessions: list[ChatSession] = []
        for source_path in self.discover_files(root, patterns):
            for payload in self.parse_json_payloads(source_path):
                timestamp_raw = payload.get("timestamp") or payload.get("started_at")
                timestamp = _parse_timestamp(timestamp_raw)
                if timestamp is None:
                    continue
                raw_items: Any = (
                    payload.get("messages")
                    or payload.get("events")
                    or payload.get("steps")
                )
                items_list: list[Any] = raw_items if isinstance(raw_items, list) else []
                processed: list[dict[str, Any]] = []
                for item in items_list:
                    if isinstance(item, dict):
                        step_id = item.get("id") or item.get("step_id")
                        processed.append(
                            {
                                **item,
                                "native_id": str(step_id) if step_id else None,
                            }
                        )
                messages = self.parse_messages(processed)
                if not messages:
                    continue
                model = str(
                    payload.get("model") or payload.get("agent_model") or "unknown"
                )
                source_record_id = str(
                    payload.get("trace_id")
                    or payload.get("id")
                    or payload.get("run_id")
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
