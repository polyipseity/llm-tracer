"""oterm SQLite adapter implementation.

oterm stores chats in SQLite at `store.db` under its app data directory.
"""

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from llm_tracer.adapters.base import BaseAdapter
from llm_tracer.schema import AttachmentPolicy
from llm_tracer.schema.v1 import ChatSessionV1

"""Public symbols exported by this module."""
__all__ = ("OTermAdapter",)


class OTermAdapter(BaseAdapter):
    """Normalize oterm SQLite chat/message records into ``ChatSessionV1``."""

    source_slug = "oterm"

    def default_roots(self, *, options: dict[str, str]) -> list[Path]:
        """Return default oterm app-data roots across major platforms."""

        del options
        roots = [
            Path.home() / "Library" / "Application Support" / "oterm",
            Path.home() / ".local" / "share" / "oterm",
        ]
        appdata = os.environ.get("APPDATA")
        if appdata:
            roots.append(Path(appdata) / "oterm")
        return roots

    def ingest(self, root: Path, patterns: list[str]) -> list[ChatSessionV1]:
        """Ingest one or more oterm SQLite databases from the provided root."""

        candidate_dbs: list[Path] = []
        if root.is_file() and root.suffix == ".db":
            candidate_dbs.append(root)
        db_at_root = root / "store.db"
        if db_at_root.exists():
            candidate_dbs.append(db_at_root)
        for discovered in self.discover_files(root, patterns):
            if discovered.suffix == ".db":
                candidate_dbs.append(discovered)

        sessions: list[ChatSessionV1] = []
        for db_path in sorted(set(candidate_dbs)):
            sessions.extend(_ingest_store_db(self, db_path, root))
        return sessions


def _ingest_store_db(
    adapter: OTermAdapter,
    db_path: Path,
    root: Path,
) -> list[ChatSessionV1]:
    """Convert one oterm `store.db` into normalized chat sessions."""

    try:
        connection = sqlite3.connect(db_path)
    except sqlite3.Error:
        return []
    connection.row_factory = sqlite3.Row

    try:
        chat_rows = connection.execute(
            "SELECT id, name, model FROM chat ORDER BY id"
        ).fetchall()
        message_rows = connection.execute(
            "SELECT id, chat_id, author, text FROM message ORDER BY id"
        ).fetchall()
    except sqlite3.Error:
        connection.close()
        return []
    connection.close()

    messages_by_chat: dict[int, list[sqlite3.Row]] = {}
    for row in message_rows:
        chat_id = int(row["chat_id"])
        messages_by_chat.setdefault(chat_id, []).append(row)

    timestamp = datetime.fromtimestamp(db_path.stat().st_mtime, tz=UTC)
    folder = db_path.parent.name if db_path.parent != root else None

    sessions: list[ChatSessionV1] = []
    for chat in chat_rows:
        chat_id = int(chat["id"])
        raw_messages = messages_by_chat.get(chat_id, [])
        if not raw_messages:
            continue
        normalized_rows = [
            {
                "role": _normalize_author(str(message["author"])),
                "content": str(message["text"]),
                "native_id": f"message:{int(message['id'])}",
            }
            for message in raw_messages
            if str(message["text"]).strip()
        ]
        parsed = adapter.parse_messages(
            normalized_rows,
            attachment_policy=AttachmentPolicy.METADATA_ONLY,
        )
        if not parsed:
            continue

        title_raw = chat["name"]
        model_raw = chat["model"]
        sessions.append(
            adapter.build_chat_session(  # type: ignore[arg-type]
                source_record_id=f"chat:{chat_id}",
                source_path=db_path,
                source_root=root,
                timestamp=timestamp,
                model=str(model_raw) if model_raw is not None else "unknown",
                messages=parsed,
                tags=[],
                title=str(title_raw) if title_raw else None,
                folder=folder,
                attachment_policy=AttachmentPolicy.METADATA_ONLY,
            )
        )
    return sessions


def _normalize_author(author: str) -> str:
    """Map oterm message author values to normalized message roles."""

    lowered = author.strip().lower()
    if lowered in {"user", "assistant", "system", "tool"}:
        return lowered
    return "assistant"
