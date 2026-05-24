"""Demo: ingest an OpenCode session using OpenCodeAdapter.

OpenCode (https://opencode.ai) stored sessions and messages as **separate**
JSON files under ``~/.local/share/opencode/storage/`` before migrating to
SQLite (approximately April 2025). The old JSON format uses:

- ``storage/session/<projectID>/<sessionID>.json`` — session metadata with
  ``title`` and ``time.created`` (epoch ms).
- ``storage/message/<sessionID>/<messageID>.json`` — individual messages with
  ``role``, ``parts`` (text array), and ``metadata.sessionID`` linking back to
  the session.

``OpenCodeAdapter`` discovers all JSON files, classifies them as session files
or message files, and assembles ``ChatSession`` records by matching messages to
sessions via ``metadata.sessionID``.

Sources
-------
- XDG data-home path (global.ts):
  https://github.com/sst/opencode/blob/dev/packages/core/src/global.ts
- OpenCode JSON migration source (json-migration.ts):
  https://github.com/sst/opencode/blob/dev/packages/opencode/src/storage/json-migration.ts
- Message v1 schema (inline parts):
  https://github.com/sst/opencode/blob/dev/packages/opencode/src/session/message.ts
"""

from pathlib import Path

from llm_tracer.adapters.opencode import OpenCodeAdapter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "opencode" / "storage"


def main() -> None:
    """Ingest the OpenCode multi-file fixture and assert expected session structure."""
    adapter = OpenCodeAdapter()
    sessions = adapter.ingest(FIXTURE_DIR, ["**/*.json", "**/*.jsonl"])

    assert sessions, "expected at least one session from OpenCode fixture"
    session = sessions[0]
    assert session.source == "opencode", f"unexpected source: {session.source}"
    assert session.model, "model should be non-empty"
    assert len(session.messages) == 4, (
        f"expected 4 messages, got {len(session.messages)}"
    )
    assert session.messages[0].role == "user"
    assert session.messages[1].role == "assistant"
    assert session.messages[2].role == "user"
    assert session.messages[3].role == "assistant"
    assert "import/workspaces/llm-tracer" in session.tags, (
        f"missing import/workspaces/llm-tracer tag; got: {session.tags}"
    )

    print(f"OpenCodeAdapter: parsed {len(sessions)} session(s)")
    for s in sessions:
        print(f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)}")


if __name__ == "__main__":
    main()
