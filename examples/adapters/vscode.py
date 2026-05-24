"""Demo: ingest a VS Code Copilot Chat session using VSCodeAdapter.

VS Code Copilot Chat stores sessions as JSONL mutation logs.  The real storage
layout uses a per-workspace directory hierarchy:
``User/workspaceStorage/{32-hex-hash}/chatSessions/{session-uuid}.jsonl``
where the 32-char hex hash is an MD5 of the workspace folder path.
Empty-window and transferred sessions go under ``globalStorage/``.

Platform roots:
- macOS (stable):   ``~/Library/Application Support/Code/User/``
- macOS (Insiders): ``~/Library/Application Support/Code - Insiders/User/``
- Linux (stable):   ``~/.config/Code/User/``
- Linux (Insiders): ``~/.config/Code - Insiders/User/``
- Windows:          ``%APPDATA%\\Code\\User\\``

The fixture here reproduces a real-format directory tree with two request-
response turns, demonstrating workspace_id extraction and the mutation-log
round-trip through ``VSCodeAdapter``.

Sources
-------
- Storage paths: https://github.com/digitarald/vscode-session-trace/blob/main/README.md
- Type definitions: https://github.com/digitarald/vscode-session-trace/blob/main/src/types.ts
- VS Code issue confirming path: https://github.com/microsoft/vscode/issues/312610
"""

from pathlib import Path

from llm_tracer.adapters.vscode import VSCodeAdapter

"Fixture root pointing at the workspaceStorage subdirectory of the VS Code fixture tree."
FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "vscode" / "workspaceStorage"


def main() -> None:
    """Ingest the VS Code JSONL fixture and assert expected session structure."""
    adapter = VSCodeAdapter()
    sessions = adapter.ingest(FIXTURE_DIR, ["**/*.json", "**/*.jsonl"])

    assert sessions, "expected at least one session from VS Code fixture"
    session = sessions[0]
    assert session.source == "vscode", f"unexpected source: {session.source}"
    assert session.model, "model should be non-empty"
    assert len(session.messages) >= 4, "expected 2 user + 2 assistant turns"
    assert session.messages[0].role == "user"
    assert session.messages[1].role == "assistant"
    assert any("vscode" in tag for tag in session.tags), "missing vscode id tag"

    workspace_id_tags = [
        t for t in session.tags if t.startswith("import/workspace_ids/")
    ]
    assert workspace_id_tags, "missing import/workspace_ids/* tag"
    assert "baed92910affe51bce3aeb07d38a7955" in workspace_id_tags[0], (
        f"workspace_id tag does not contain expected hash: {workspace_id_tags}"
    )

    print(f"VSCodeAdapter: parsed {len(sessions)} session(s)")
    for s in sessions:
        print(
            f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)} tags={s.tags}"
        )


if __name__ == "__main__":
    main()
