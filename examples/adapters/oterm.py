"""Demo: ingest oterm chats from a temporary SQLite store.db."""

import sqlite3
import tempfile
from pathlib import Path

from llm_tracer.adapters.oterm import OTermAdapter


def _build_fixture_db(path: Path) -> None:
    """Create a minimal oterm-compatible SQLite dataset for demo ingestion."""

    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            model TEXT NOT NULL,
            system TEXT,
            format TEXT,
            parameters TEXT DEFAULT '{}',
            keep_alive INTEGER DEFAULT 5,
            tools TEXT DEFAULT '[]',
            thinking BOOLEAN DEFAULT 0
        );
        CREATE TABLE message (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            text TEXT NOT NULL,
            images TEXT DEFAULT '[]',
            FOREIGN KEY(chat_id) REFERENCES chat(id) ON DELETE CASCADE
        );
        INSERT INTO chat(id, name, model) VALUES (1, 'demo', 'llama3.1');
        INSERT INTO message(chat_id, author, text) VALUES (1, 'user', 'hello');
        INSERT INTO message(chat_id, author, text) VALUES (1, 'assistant', 'hi');
        """
    )
    connection.commit()
    connection.close()


def main() -> None:
    """Build a temporary oterm DB, ingest it, and verify normalized output."""

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "store.db"
        _build_fixture_db(db_path)

        adapter = OTermAdapter()
        sessions = adapter.ingest(db_path.parent, ["**/*.db"])

        assert sessions, "expected at least one oterm session"
        session = sessions[0]
        assert session.source == "oterm"
        assert session.model == "llama3.1"
        assert [message.role for message in session.messages] == ["user", "assistant"]


if __name__ == "__main__":
    main()
