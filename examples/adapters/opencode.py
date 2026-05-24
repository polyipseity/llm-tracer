"""Demo: ingest an OpenCode session using OpenCodeAdapter.

OpenCode (https://opencode.ai) migrated from a JSON-file backend to SQLite
in a recent release. The previous JSON storage kept session metadata at
``storage/session/<projectID>/<sessionID>.json`` and individual messages at
``storage/message/<sessionID>/<messageID>.json`` — with sessions and messages
stored separately (source: json-migration.ts at
https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/storage/json-migration.ts).

The current ``OpenCodeAdapter`` targets a simplified **inline** format — a
single JSON file per session where messages are embedded directly — which
corresponds to a hypothetical export or legacy single-file format. The fixture
here exercises that path: ``id``, ``createdAt`` (ISO string), ``model``,
``title``, and an inline ``messages`` array.

Sources
-------
- OpenCode JSON migration source:
  https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/storage/json-migration.ts
- OpenCode project: https://opencode.ai
"""

from pathlib import Path

from llm_tracer.adapters.opencode import OpenCodeAdapter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "opencode"


def main() -> None:
    """Ingest the OpenCode fixture and assert expected session structure."""
    adapter = OpenCodeAdapter()
    sessions = adapter.ingest(FIXTURE_DIR, ["**/*.json", "**/*.jsonl"])

    assert sessions, "expected at least one session from OpenCode fixture"
    session = sessions[0]
    assert session.source == "opencode", f"unexpected source: {session.source}"
    assert session.model, "model should be non-empty"
    assert len(session.messages) >= 2, "expected user + assistant turns"
    assert session.messages[0].role == "user"
    assert session.messages[1].role == "assistant"
    assert any("opencode" in tag for tag in session.tags), "missing opencode id tag"

    print(f"OpenCodeAdapter: parsed {len(sessions)} session(s)")
    for s in sessions:
        print(f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)}")


if __name__ == "__main__":
    main()
