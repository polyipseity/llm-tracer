"""VS Code Copilot Chat adapter implementation.

VS Code Copilot Chat stores sessions as JSONL mutation logs at
``workspaceStorage/<uuid>/chatSessions/<session-uuid>.jsonl`` (per-workspace)
or ``globalStorage/emptyWindowChatSessions/<uuid>.jsonl`` (empty window).

Format (VS Code ≥ 1.109 / github.copilot-chat ≥ 0.47.0, released Feb 2026):
each line is a JSON object discriminated by ``kind``:

- ``kind 0``: full ``SerializableChatData`` snapshot, always the first line,
  value in ``v``.
- ``kind 1``: set a nested property; path in ``k``, value in ``v``.
- ``kind 2``: append items to a nested array; path in ``k``, items in ``v``.
- ``kind 3``: delete a nested property; path in ``k``.

Key ``SerializableChatData`` fields::

    sessionId     – UUID string, matches the filename
    creationDate  – session creation time, epoch milliseconds (integer)
    customTitle   – AI- or user-set title, arrives as a ``kind:1`` patch
    requests      – list of ``SerializableChatRequest`` objects

Key ``SerializableChatRequest`` fields::

    requestId  – "request_<uuid>"
    timestamp  – epoch milliseconds
    modelId    – model identifier (e.g. "gpt-4o", "copilot/auto")
    message    – {"text": <user prompt string>, "parts": []}
    response   – list of heterogeneous parts; text parts carry
                 ``kind="text"`` and ``content=<string>``

Sources
-------
- ``digitarald/vscode-session-trace`` type definitions:
  https://github.com/digitarald/vscode-session-trace/blob/main/src/types.ts
- DeepWiki schema reference:
  https://deepwiki.com/digitarald/vscode-session-trace/2.2-data-types-and-serialization-schema
- VS Code issue confirming JSONL path and format:
  https://github.com/microsoft/vscode/issues/312610
- Format transition confirmed in:
  https://github.com/microsoft/vscode/issues/291374
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from llm_tracer.adapters.base import BaseAdapter
from llm_tracer.core.schema import ChatSession

"""Public symbols exported by this module."""
__all__ = ("VSCodeAdapter",)


class VSCodeAdapter(BaseAdapter):
    """Normalize VS Code Copilot Chat JSONL sessions into ``ChatSession`` records."""

    source_slug = "vscode"

    def default_roots(self, *, options: dict[str, str]) -> list[Path]:
        """Return default VS Code workspace storage roots."""

        del options
        home = Path.home()
        return [
            home / "Library/Application Support/Code/User/workspaceStorage",
            home / "Library/Application Support/Code - Insiders/User/workspaceStorage",
        ]

    def ingest(self, root: Path, patterns: list[str]) -> list[ChatSession]:
        """Ingest VS Code JSONL session files and return normalized sessions."""

        sessions: list[ChatSession] = []
        for source_path in self.discover_files(root, patterns):
            if source_path.suffix.lower() != ".jsonl":
                continue
            session = _ingest_jsonl(self, source_path, root)
            if session is not None:
                sessions.append(session)
        return sessions


def _ingest_jsonl(
    adapter: VSCodeAdapter, source_path: Path, root: Path
) -> ChatSession | None:
    """Replay a VS Code JSONL mutation log and build a ``ChatSession``."""

    state: dict[str, Any] = {}
    with source_path.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                _apply_mutation(state, entry)
    return _build_session(adapter, state, source_path, root)


def _build_session(
    adapter: VSCodeAdapter,
    state: dict[str, Any],
    source_path: Path,
    root: Path,
) -> ChatSession | None:
    """Build a ``ChatSession`` from a fully-replayed VS Code session state."""

    creation_date = state.get("creationDate")
    if not isinstance(creation_date, (int, float)):
        return None
    timestamp = datetime.fromtimestamp(creation_date / 1000.0, tz=UTC)

    requests: Any = state.get("requests") or []
    if not isinstance(requests, list) or not requests:
        return None

    normalized: list[dict[str, Any]] = []
    model = "unknown"
    for req in requests:
        if not isinstance(req, dict):
            continue
        if model == "unknown" and req.get("modelId"):
            model = str(req["modelId"])
        msg_obj = req.get("message")
        if isinstance(msg_obj, dict):
            user_text = str(msg_obj.get("text") or "").strip()
            if user_text:
                normalized.append({"role": "user", "content": user_text})
        response: Any = req.get("response") or []
        if isinstance(response, list):
            text_parts = [
                str(part.get("content") or "")
                for part in response
                if isinstance(part, dict) and part.get("kind") == "text"
            ]
            asst_text = "".join(text_parts).strip()
            if asst_text:
                normalized.append({"role": "assistant", "content": asst_text})

    messages = adapter.parse_messages(normalized)
    if not messages:
        return None

    session_id = str(state.get("sessionId") or uuid4())
    title_raw = state.get("customTitle")
    return adapter.build_chat_session(
        source_record_id=session_id,
        source_path=source_path,
        source_root=root,
        timestamp=timestamp,
        model=model,
        messages=messages,
        tags=[],
        title=str(title_raw) if title_raw else None,
    )


def _apply_mutation(state: dict[str, Any], entry: dict[str, Any]) -> None:
    """Apply one JSONL mutation entry to the mutable session state dict in place."""

    kind = entry.get("kind")
    if kind == 0:
        v = entry.get("v")
        state.clear()
        if isinstance(v, dict):
            state.update(v)
    elif kind == 1:
        path: list[Any] = entry.get("k") or []
        _set_at_path(state, path, entry.get("v"))
    elif kind == 2:
        path = entry.get("k") or []
        new_items = entry.get("v")
        existing = _get_at_path(state, path)
        if isinstance(existing, list) and isinstance(new_items, list):
            existing.extend(new_items)
    elif kind == 3:
        path = entry.get("k") or []
        _del_at_path(state, path)


def _get_at_path(obj: Any, path: list[Any]) -> Any:
    """Retrieve the value at a nested path (list of keys/indices) within obj."""

    current: Any = obj
    for key in path:
        if isinstance(current, dict) and isinstance(key, str):
            current = current.get(key)
        elif isinstance(current, list) and isinstance(key, int):
            current = current[key] if 0 <= key < len(current) else None
        else:
            return None
    return current


def _set_at_path(obj: dict[str, Any], path: list[Any], value: Any) -> None:
    """Set value at a nested path (list of keys/indices) within obj."""

    if not path:
        return
    current: Any = obj
    for key in path[:-1]:
        if isinstance(current, dict) and isinstance(key, str):
            next_val = current.get(key)
            if next_val is None:
                return
            current = next_val
        elif (
            isinstance(current, list)
            and isinstance(key, int)
            and 0 <= key < len(current)
        ):
            current = current[key]
        else:
            return
    last = path[-1]
    if isinstance(current, dict) and isinstance(last, str):
        current[last] = value
    elif (
        isinstance(current, list) and isinstance(last, int) and 0 <= last < len(current)
    ):
        current[last] = value


def _del_at_path(obj: dict[str, Any], path: list[Any]) -> None:
    """Delete the value at a nested path (list of keys/indices) within obj."""

    if not path:
        return
    current: Any = obj
    for key in path[:-1]:
        if isinstance(current, dict) and isinstance(key, str):
            current = current.get(key)
        elif (
            isinstance(current, list)
            and isinstance(key, int)
            and 0 <= key < len(current)
        ):
            current = current[key]
        else:
            return
    last = path[-1]
    if isinstance(current, dict) and isinstance(last, str):
        current.pop(last, None)
    elif (
        isinstance(current, list) and isinstance(last, int) and 0 <= last < len(current)
    ):
        del current[last]
