"""Demo: ingest a VS Code Copilot Chat session using VSCodeAdapter.

VS Code Copilot Chat stores sessions internally as patch-based JSONL files in
``workspaceStorage/<uuid>/chatSessions/<session-id>.jsonl`` (verified by
inspection of local VS Code workspace storage). Each line carries a ``kind``
field (0 = initializer, 1 = patch) and uses ``creationDate`` (integer
milliseconds) rather than ISO strings.

This example uses a **simplified JSON export** format matching the fields that
``VSCodeAdapter`` was designed to parse: ``sessionId``, ``createdAt`` (ISO
string), ``model``, ``title``, and a ``messages`` array of ``{role, content}``
objects. The fixture demonstrates a clean round-trip through the adapter.

Sources
-------
- VS Code workspace storage format observed at
  ``~/Library/Application Support/Code - Insiders/User/workspaceStorage/``
  (local inspection, 2025).
"""

from pathlib import Path

from llm_tracer.adapters.vscode import VSCodeAdapter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "vscode"


def main() -> None:
    """Ingest the VS Code fixture and assert expected session structure."""
    adapter = VSCodeAdapter()
    sessions = adapter.ingest(FIXTURE_DIR, ["**/*.json", "**/*.jsonl"])

    assert sessions, "expected at least one session from VS Code fixture"
    session = sessions[0]
    assert session.source == "vscode", f"unexpected source: {session.source}"
    assert session.model, "model should be non-empty"
    assert len(session.messages) >= 2, "expected user + assistant turns"
    assert session.messages[0].role == "user"
    assert session.messages[1].role == "assistant"
    assert any("vscode" in tag for tag in session.tags), "missing vscode id tag"

    print(f"VSCodeAdapter: parsed {len(sessions)} session(s)")
    for s in sessions:
        print(
            f"  id={s.id[:8]}... model={s.model!r}"
            f" msgs={len(s.messages)} title={s.tags}"
        )


if __name__ == "__main__":
    main()
