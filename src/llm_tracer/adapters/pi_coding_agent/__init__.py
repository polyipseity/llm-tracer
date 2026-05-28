"""PI agent trace adapter implementation.

PI Coding Agent stores local state under ``~/.pi/agent``. Session transcripts
are persisted as JSONL event streams under ``sessions/<project>/``. Legacy
single-object JSON traces are still supported as a structural fallback.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from lenses import bind

from llm_tracer.adapters.base import BaseAdapter
from llm_tracer.adapters.pi_coding_agent.raw.v2025_01 import PiCodingAgentTraceV2025_01
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
        return [home / ".pi" / "agent"]

    def ingest(self, root: Path, patterns: list[str]) -> list[ChatSessionV1]:
        """Ingest and normalize PI-agent trace files from a root directory."""

        sessions: list[ChatSessionV1] = []
        for source_path in self.discover_files(root, patterns):
            payloads = self.parse_json_payloads(source_path)
            event_stream_session = _ingest_event_stream(
                adapter=self,
                payloads=payloads,
                source_path=source_path,
                root=root,
            )
            if event_stream_session is not None:
                sessions.append(event_stream_session)
                continue
            for payload in payloads:
                trace = _parse_trace_file(payload, source_path)
                if trace is None:
                    continue
                session = _ingest_one_trace(self, trace, source_path, root)
                if session is not None:
                    sessions.append(session)
        return sessions


def _ingest_event_stream(
    *,
    adapter: PiCodingAgentAdapter,
    payloads: list[dict[str, Any]],
    source_path: Path,
    root: Path,
) -> ChatSessionV1 | None:
    """Parse one PI JSONL event stream into a single normalized chat session."""

    if not payloads:
        return None
    header = next(
        (
            payload
            for payload in payloads
            if payload.get("type") == "session" and isinstance(payload.get("id"), str)
        ),
        None,
    )
    if header is None:
        return None

    message_rows: list[dict[str, Any]] = []
    model = "unknown"
    for payload in payloads:
        payload_type = payload.get("type")
        if payload_type == "model_change" and payload.get("modelId") is not None:
            model = str(payload["modelId"])
            continue
        if payload_type != "message":
            continue
        message = payload.get("message")
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "assistant")
        text = _extract_event_message_text(message.get("content"))
        if not text:
            continue
        native_id = payload.get("id")
        message_rows.append(
            {
                "role": role,
                "content": text,
                "native_id": str(native_id) if native_id is not None else None,
            }
        )
        if model == "unknown" and message.get("model") is not None:
            model = str(message["model"])

    messages = adapter.parse_messages(message_rows)
    if not messages:
        return None

    session_timestamp = _parse_timestamp(header.get("timestamp"))
    if session_timestamp is None:
        session_timestamp = datetime.fromtimestamp(source_path.stat().st_mtime, tz=UTC)

    source_record_id = str(header.get("id") or source_path.stem)
    folder = _extract_workspace_folder(source_path.parent.name)
    return adapter.build_chat_session(  # type: ignore[return-value]
        source_record_id=source_record_id,
        source_path=source_path,
        source_root=root,
        timestamp=session_timestamp,
        model=model,
        messages=messages,
        tags=[],
        title=None,
        folder=folder,
    )


def _extract_event_message_text(content: object) -> str:
    """Extract text from heterogeneous PI/Codex-style event message content."""

    if isinstance(content, str):
        return content.strip()
    if isinstance(content, dict):
        content_dict = cast("dict[str, Any]", content)
        text_value = content_dict.get("text")
        return str(text_value).strip() if text_value is not None else ""
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            item_dict = cast("dict[str, Any]", item)
            if item_dict.get("type") != "text":
                continue
            text_value = item_dict.get("text")
            if text_value is None:
                continue
            text = str(text_value).strip()
            if text:
                chunks.append(text)
        return "\n".join(chunks).strip()
    return ""


def _extract_workspace_folder(folder_dir_name: str) -> str:
    """Extract innermost folder name from workspace directory.

    PI agent encodes workspace paths as `--{path_with_slashes_as_dashes}--`.
    This function detects and decodes such paths, extracting only the
    final path component (e.g., project name).

    Example: `--Users-polyipseity-dev-monorepo-self-llm-tracer--` → `llm-tracer`
    """

    # Check if this is an encoded full path (surrounded by --)
    if folder_dir_name.startswith("--") and folder_dir_name.endswith("--"):
        # Decode: strip --, replace - with / to reconstruct path
        encoded = folder_dir_name[2:-2]
        reconstructed_path = encoded.replace("-", "/")
        # Extract innermost component
        return reconstructed_path.split("/")[-1]
    # Not encoded; use as-is
    return folder_dir_name


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
    tags = _filter_upstream_import_tags(tags_raw)
    folder = _extract_workspace_folder(source_path.parent.name)
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


def _filter_upstream_import_tags(tags_raw: object) -> list[str]:
    """Keep only non-import tags from upstream traces.

    Import tags are regenerated locally from normalized fields so that
    workspace/title/id tags stay deterministic and do not embed full paths.
    """

    if not isinstance(tags_raw, list):
        return []
    return [
        str(tag)
        for tag in tags_raw
        if isinstance(tag, str) and not tag.startswith("import/")
    ]


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
