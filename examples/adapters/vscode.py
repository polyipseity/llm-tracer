"""Demo: ingest a VS Code Copilot Chat session using VSCodeAdapter.

VS Code Copilot Chat stores sessions as JSONL mutation logs at
``workspaceStorage/<uuid>/chatSessions/<session-uuid>.jsonl`` on all platforms
(per-workspace sessions). Empty-window sessions go to
``globalStorage/emptyWindowChatSessions/<uuid>.jsonl``.

Format (VS Code ≥ 1.109 / github.copilot-chat ≥ 0.47.0, released Feb 2026):
each line is one JSON object with a ``kind`` discriminator (0 = full snapshot,
1 = set property at path, 2 = append to array, 3 = delete property).

The fixture here reproduces a minimal real-format session with one user turn
and one assistant response, demonstrating the mutation-log round-trip through
``VSCodeAdapter``.

Sources
-------
- Type definitions: https://github.com/digitarald/vscode-session-trace/blob/main/src/types.ts
- VS Code issue confirming path: https://github.com/microsoft/vscode/issues/312610
"""

from pathlib import Path

from llm_tracer.adapters.vscode import VSCodeAdapter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "vscode"


def main() -> None:
    """Ingest the VS Code JSONL fixture and assert expected session structure."""
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
            f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)} tags={s.tags}"
        )


if __name__ == "__main__":
    main()
