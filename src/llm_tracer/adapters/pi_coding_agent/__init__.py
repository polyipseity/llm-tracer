"""PI agent trace adapter implementation.

Note: Storage paths and trace format are speculative — no public documentation
was found for PI Coding Agent's data storage format.  The default roots and
field names were inferred by reverse-engineering locally captured traces.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from lenses import bind

from llm_tracer.adapters.base import BaseAdapter
from llm_tracer.adapters.pi_coding_agent.raw.v2025_01 import (
    PiCodingAgentTraceV2025_01,
)
from llm_tracer.schema.v1 import ChatSessionV1

"""Public symbols exported by this module."""
__all__ = ("PiCodingAgentAdapter",)


class PiCodingAgentAdapter(BaseAdapter):
    """Normalize PI-agent execution traces into ``ChatSessionV1`` records."""

    source_slug = "pi_coding_agent"

    def default_roots(self, *, options: dict[str, str]) -> list[Path]:
        """Return default PI coding agent trace directories."""

        del options
        home = Path.home()
        return [
            home / ".pi-agent",
            home / "Library/Application Support/PiAgent",
        ]

    def ingest(self, root: Path, patterns: list[str]) -> list[ChatSessionV1]:
        """Ingest and normalize PI-agent trace files from a root directory."""

        sessions: list[ChatSessionV1] = []
        for source_path in self.discover_files(root, patterns):
            for payload in self.parse_json_payloads(source_path):
                trace = _parse_trace_file(payload, source_path)
                if trace is None:
                    continue
                session = _ingest_one_trace(self, trace, source_path, root)
                if session is not None:
                    sessions.append(session)
        return sessions


def _try_parse_v2025_01(raw: dict[str, Any]) -> PiCodingAgentTraceV2025_01 | None:
    """Try to parse payload as PI Coding Agent 2025-01 format.

    Structural check based on reverse-engineered format.
    """
    has_content = any(k in raw for k in ("messages", "events", "steps", "turns"))
    if not has_content:
        return None
    return cast("PiCodingAgentTraceV2025_01", raw)


def _parse_trace_file(
    raw: dict[str, Any], source_path: Path
) -> PiCodingAgentTraceV2025_01 | None:
    """Parse a PI Coding Agent trace JSON file using structural fallback.

    The format is undocumented; structural detection is used as a proxy.
    The latest known schema is tried first; older schemas can be added
    below when discovered.
    """
    del source_path
    result = _try_parse_v2025_01(raw)
    if result is not None:
        return result
    # Future: add older format fallback branches here
    return None


def _ingest_one_trace(
    adapter: PiCodingAgentAdapter,
    trace: PiCodingAgentTraceV2025_01,
    source_path: Path,
    root: Path,
) -> ChatSessionV1 | None:
    """Apply the bidirectional lens to extract one ChatSessionV1."""

    def getter(t: PiCodingAgentTraceV2025_01) -> ChatSessionV1 | None:
        """Forward lens: PI agent trace → ChatSessionV1."""
        return _to_unified(adapter, t, source_path, root)

    def setter(
        t: PiCodingAgentTraceV2025_01, unified: ChatSessionV1
    ) -> PiCodingAgentTraceV2025_01:
        """Backward lens: ChatSessionV1 → PI agent trace."""
        return _to_upstream_trace(t, unified)

    return bind(trace).Lens(getter, setter).get()  # type: ignore[no-any-return]


def _to_unified(
    adapter: PiCodingAgentAdapter,
    trace: PiCodingAgentTraceV2025_01,
    source_path: Path,
    root: Path,
) -> ChatSessionV1 | None:
    """Forward lens: PI agent trace → ChatSessionV1.

    This is the getter half of the bidirectional lens.
    """

    timestamp_raw = trace.get("timestamp") or trace.get("started_at")
    timestamp = _parse_timestamp(timestamp_raw)
    if timestamp is None:
        return None

    raw_items: Any = trace.get("messages") or trace.get("events") or trace.get("steps")
    items_list: list[Any] = raw_items if isinstance(raw_items, list) else []
    processed: list[dict[str, Any]] = []
    for item in items_list:
        if isinstance(item, dict):
            item_d = cast("dict[str, Any]", item)
            step_id = item_d.get("id") or item_d.get("step_id")
            processed.append(
                {
                    **item_d,
                    "native_id": str(step_id) if step_id else None,
                }
            )
    messages = adapter.parse_messages(processed)
    if not messages:
        return None

    model = str(trace.get("model") or trace.get("agent_model") or "unknown")
    source_record_id = str(
        trace.get("trace_id") or trace.get("id") or trace.get("run_id") or uuid4()
    )
    title = trace.get("title") or trace.get("name")
    tags_raw = trace.get("tags")
    tags = [str(tag) for tag in tags_raw] if isinstance(tags_raw, list) else []
    folder = source_path.parent.name if source_path.parent != root else None
    return adapter.build_chat_session(  # type: ignore[return-value]
        source_record_id=source_record_id,
        source_path=source_path,
        source_root=root,
        timestamp=timestamp,
        model=model,
        messages=messages,
        tags=tags,
        title=str(title) if title is not None else None,
        folder=folder,
    )


def _to_upstream_trace(
    trace: PiCodingAgentTraceV2025_01,
    unified: ChatSessionV1,
) -> PiCodingAgentTraceV2025_01:
    """Backward lens: unified ChatSessionV1 → PI agent trace.

    Writes back the title and tags.  All other unified metadata is dropped (lossy).
    """

    result: dict[str, Any] = {**trace}
    for tag in unified.tags:
        if tag.startswith("import/title/"):
            result["title"] = tag[len("import/title/") :]
            break
    return cast("PiCodingAgentTraceV2025_01", result)


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
