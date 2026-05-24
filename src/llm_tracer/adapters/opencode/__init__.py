"""OpenCode session and message adapter implementation.

OpenCode (https://opencode.ai) stored sessions and messages as separate JSON
files under ``$XDG_DATA_HOME/opencode/storage/`` in its pre-SQLite format.
On macOS and Linux ``$XDG_DATA_HOME`` defaults to ``~/.local/share``, so the
full storage root is::

    ~/.local/share/opencode/storage/

Directory layout::

    storage/session/<projectID>/<sessionID>.json   — session metadata
    storage/message/<sessionID>/<messageID>.json   — individual messages
    storage/part/<messageID>/<partID>.json         — message parts (v2 only)

Current versions (since approximately February 2026) use a SQLite database at
``$XDG_DATA_HOME/opencode/opencode.db``. This adapter targets the earlier
JSON storage format that was in use from OpenCode's first public release
(v0.0.45, 2025-05-15) until that migration.

Session file schema::

    title   – session title (string)
    slug    – URL-friendly slug
    version – opencode version string
    time    – {"created": <epoch_ms>, "updated": <epoch_ms>}

Message file schema (v1 — parts inline)::

    id       – message ID
    role     – "user" | "assistant"
    parts    – list of {"type": "text", "text": "..."}
    metadata – {
        "sessionID": "<session file stem>",
        "time":      {"created": <epoch_ms>, "completed": <epoch_ms>},
        "assistant": {"modelID": "...", "providerID": "..."}  (assistant only)
    }

This adapter:
1. Classifies discovered JSON files as session files (contain ``time.created``)
   or message files (contain ``role`` + ``parts``).
2. Groups messages by ``metadata.sessionID``, matching to session file stems.
3. Sorts messages by ``metadata.time.created`` and assembles ``ChatSession``
   records.

Sources
-------
- XDG data-home path (global.ts):
  https://github.com/sst/opencode/blob/dev/packages/core/src/global.ts
- OpenCode JSON migration source (json-migration.ts):
  https://github.com/sst/opencode/blob/dev/packages/opencode/src/storage/json-migration.ts
- Message v1 schema (inline parts):
  https://github.com/sst/opencode/blob/dev/packages/opencode/src/session/message.ts
- OpenCode project: https://opencode.ai
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from lenses import bind

from llm_tracer.adapters.base import BaseAdapter
from llm_tracer.adapters.opencode.raw.v2025_05 import (
    OpenCodeMessageDataV2025_05,
    OpenCodeSessionDataV2025_05,
    OpenCodeSessionStateV2025_05,
)
from llm_tracer.core.schema.v1 import ChatSessionV1

"""Public symbols exported by this module."""
__all__ = ("OpenCodeAdapter",)


class OpenCodeAdapter(BaseAdapter):
    """Normalize OpenCode JSON session and message files into ``ChatSessionV1`` records."""

    source_slug = "opencode"

    def default_roots(self, *, options: dict[str, str]) -> list[Path]:
        """Return the default OpenCode JSON storage root.

        Uses the XDG_DATA_HOME convention: ``~/.local/share/opencode/storage``.
        Source: https://github.com/sst/opencode/blob/dev/packages/core/src/global.ts
        """

        del options
        home = Path.home()
        return [
            home / ".local" / "share" / "opencode" / "storage",
        ]

    def ingest(self, root: Path, patterns: list[str]) -> list[ChatSessionV1]:
        """Ingest and normalize OpenCode session and message files from a root directory."""

        session_map: dict[str, tuple[Path, OpenCodeSessionDataV2025_05]] = {}
        message_groups: dict[str, list[OpenCodeMessageDataV2025_05]] = {}

        for source_path in self.discover_files(root, patterns):
            for payload in self.parse_json_payloads(source_path):
                if "role" in payload and "parts" in payload:
                    msg = cast("OpenCodeMessageDataV2025_05", payload)
                    meta: Any = msg.get("metadata")
                    session_id = (
                        meta.get("sessionID") if isinstance(meta, dict) else None
                    )
                    if isinstance(session_id, str) and session_id:
                        message_groups.setdefault(session_id, []).append(msg)
                elif isinstance(payload.get("time"), dict) and "created" in payload.get(
                    "time", {}
                ):
                    session_map[source_path.stem] = (
                        source_path,
                        cast("OpenCodeSessionDataV2025_05", payload),
                    )

        sessions: list[ChatSessionV1] = []
        for session_id, (source_path, session_data) in session_map.items():
            state = OpenCodeSessionStateV2025_05(
                session_id=session_id,
                source_path=str(source_path),
                session=session_data,
                messages=message_groups.get(session_id, []),
            )
            session = _ingest_one_session(self, state, root)
            if session is not None:
                sessions.append(session)
        return sessions


def _ingest_one_session(
    adapter: OpenCodeAdapter,
    state: OpenCodeSessionStateV2025_05,
    root: Path,
) -> ChatSessionV1 | None:
    """Apply the bidirectional lens to extract one ChatSessionV1."""

    def getter(s: OpenCodeSessionStateV2025_05) -> ChatSessionV1 | None:
        """Forward lens: OpenCode session state → ChatSessionV1."""
        return _to_unified(adapter, s, root)

    def setter(
        s: OpenCodeSessionStateV2025_05, unified: ChatSessionV1
    ) -> OpenCodeSessionStateV2025_05:
        """Backward lens: ChatSessionV1 → OpenCode session state."""
        return _to_upstream_state(s, unified)

    return bind(state).Lens(getter, setter).get()  # type: ignore[no-any-return]


def _to_unified(
    adapter: OpenCodeAdapter,
    state: OpenCodeSessionStateV2025_05,
    root: Path,
) -> ChatSessionV1 | None:
    """Forward lens: OpenCode session state → ChatSessionV1.

    This is the getter half of the bidirectional lens.
    """

    session_id = state["session_id"]
    source_path = Path(state["source_path"])
    session_data = state["session"]
    msgs_raw = state["messages"]

    time_data: Any = session_data.get("time", {})
    created_ms = time_data.get("created") if isinstance(time_data, dict) else None
    if not isinstance(created_ms, (int, float)):
        return None
    timestamp = datetime.fromtimestamp(created_ms / 1000.0, tz=UTC)
    title_raw = session_data.get("title") or session_data.get("name")  # type: ignore[typeddict-item]

    sorted_msgs = sorted(
        msgs_raw,
        key=lambda m: (
            m["metadata"]["time"].get("created", 0)
            if isinstance(m.get("metadata"), dict)
            and isinstance(m["metadata"].get("time"), dict)
            else 0
        ),
    )
    normalized = _normalize_messages(sorted_msgs)
    messages = adapter.parse_messages(normalized)
    if not messages:
        return None

    model = _extract_model(sorted_msgs)
    return adapter.build_chat_session(  # type: ignore[return-value]
        source_record_id=session_id,
        source_path=source_path,
        source_root=root,
        timestamp=timestamp,
        model=model,
        messages=messages,
        tags=[],
        title=str(title_raw) if title_raw is not None else None,
    )


def _to_upstream_state(
    state: OpenCodeSessionStateV2025_05,
    unified: ChatSessionV1,
) -> OpenCodeSessionStateV2025_05:
    """Backward lens: unified ChatSessionV1 → OpenCode session state.

    Writes back the title.  All other unified metadata is dropped (lossy).
    """

    new_session: dict[str, Any] = {**state["session"]}
    for tag in unified.tags:
        if tag.startswith("import/title/"):
            new_session["title"] = tag[len("import/title/") :]
            break
    result: dict[str, Any] = {**state, "session": new_session}
    return cast("OpenCodeSessionStateV2025_05", result)


def _normalize_messages(
    msgs: list[OpenCodeMessageDataV2025_05],
) -> list[dict[str, Any]]:
    """Extract {role, content} dicts from OpenCode v1 message objects."""

    result: list[dict[str, Any]] = []
    for msg in msgs:
        role = str(msg.get("role", "assistant"))
        parts: Any = msg.get("parts", [])
        text = " ".join(
            p.get("text", "")
            for p in (parts if isinstance(parts, list) else [])
            if isinstance(p, dict) and p.get("type") == "text"
        ).strip()
        if text:
            msg_id = msg.get("id")
            result.append(
                {
                    "role": role,
                    "content": text,
                    "native_id": str(msg_id) if msg_id else None,
                }
            )
    return result


def _extract_model(msgs: list[OpenCodeMessageDataV2025_05]) -> str:
    """Extract model ID from the last assistant message metadata."""

    for msg in reversed(msgs):
        if msg.get("role") != "assistant":
            continue
        meta: Any = msg.get("metadata")
        if not isinstance(meta, dict):
            continue
        asst: Any = meta.get("assistant")
        if isinstance(asst, dict) and asst.get("modelID"):
            return str(asst["modelID"])
    return "unknown"
