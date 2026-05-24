"""OpenCode session and message adapter implementation.

OpenCode (https://opencode.ai) stored sessions and messages as separate JSON
files under ``$XDG_DATA_HOME/opencode/storage/`` in its pre-SQLite format:

    storage/session/<projectID>/<sessionID>.json   — session metadata
    storage/message/<sessionID>/<messageID>.json   — individual messages
    storage/part/<messageID>/<partID>.json         — message parts (v2 only)

Current versions (since approximately April 2025) use a SQLite database at
``$XDG_DATA_HOME/opencode/opencode.db``. This adapter targets the previous
JSON storage format.

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
- OpenCode JSON migration source:
  https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/storage/json-migration.ts
- Message v1 schema (inline parts):
  https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/session/message.ts
- OpenCode project: https://opencode.ai
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from llm_tracer.adapters.base import BaseAdapter
from llm_tracer.core.schema import ChatSession

"""Public symbols exported by this module."""
__all__ = ("OpenCodeAdapter",)


class OpenCodeAdapter(BaseAdapter):
    """Normalize OpenCode JSON session and message files into ``ChatSession`` records."""

    source_slug = "opencode"

    def default_roots(self, *, options: dict[str, str]) -> list[Path]:
        """Return default OpenCode JSON storage roots."""

        del options
        home = Path.home()
        return [
            home / ".local" / "share" / "opencode" / "storage",
            home / "Library/Application Support/opencode",
        ]

    def ingest(self, root: Path, patterns: list[str]) -> list[ChatSession]:
        """Ingest and normalize OpenCode session and message files from a root directory."""

        session_map: dict[str, tuple[Path, dict[str, Any]]] = {}
        message_groups: dict[str, list[dict[str, Any]]] = {}

        for source_path in self.discover_files(root, patterns):
            for payload in self.parse_json_payloads(source_path):
                if "role" in payload and "parts" in payload:
                    meta: Any = payload.get("metadata")
                    session_id = (
                        meta.get("sessionID") if isinstance(meta, dict) else None
                    )
                    if isinstance(session_id, str) and session_id:
                        message_groups.setdefault(session_id, []).append(payload)
                elif isinstance(payload.get("time"), dict) and "created" in payload.get(
                    "time", {}
                ):
                    session_map[source_path.stem] = (source_path, payload)

        sessions: list[ChatSession] = []
        for session_id, (source_path, session_data) in session_map.items():
            time_data: Any = session_data.get("time", {})
            created_ms = (
                time_data.get("created") if isinstance(time_data, dict) else None
            )
            if not isinstance(created_ms, (int, float)):
                continue
            timestamp = datetime.fromtimestamp(created_ms / 1000.0, tz=UTC)
            title_raw = session_data.get("title") or session_data.get("name")

            msgs_raw = sorted(
                message_groups.get(session_id, []),
                key=lambda m: (
                    m["metadata"]["time"].get("created", 0)
                    if isinstance(m.get("metadata"), dict)
                    and isinstance(m["metadata"].get("time"), dict)
                    else 0
                ),
            )
            normalized = _normalize_messages(msgs_raw)
            messages = self.parse_messages(normalized)
            if not messages:
                continue

            model = _extract_model(msgs_raw)
            sessions.append(
                self.build_chat_session(
                    source_record_id=session_id,
                    source_path=source_path,
                    source_root=root,
                    timestamp=timestamp,
                    model=model,
                    messages=messages,
                    tags=[],
                    title=str(title_raw) if title_raw is not None else None,
                )
            )
        return sessions


def _normalize_messages(msgs: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
            result.append({"role": role, "content": text})
    return result


def _extract_model(msgs: list[dict[str, Any]]) -> str:
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
