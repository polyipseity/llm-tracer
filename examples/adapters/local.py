"""Demo: ingest a session using LocalAdapter (auto-detection).

``LocalAdapter`` wraps all concrete adapters — ``VSCodeAdapter``,
``PiCodingAgentAdapter``, ``LMStudioAdapter``, ``OpenCodeAdapter`` — and
tries each in turn, returning the result of the first adapter that succeeds.

The fixture here is a VS Code Copilot Chat JSONL mutation log. ``LocalAdapter``
detects it via ``VSCodeAdapter`` (the first delegate it tries) and normalises
it with ``source = "vscode"``, demonstrating transparent auto-detection.

Sources
-------
- VS Code JSONL format: https://github.com/digitarald/vscode-session-trace/blob/main/src/types.ts
- LocalAdapter delegation order: ``src/llm_tracer/adapters/local.py``
"""

from pathlib import Path

from llm_tracer.adapters.local import LocalAdapter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "local"


def main() -> None:
    """Ingest the local JSONL fixture and assert auto-detected session structure."""
    adapter = LocalAdapter()
    sessions = adapter.ingest(FIXTURE_DIR, ["**/*.json", "**/*.jsonl"])

    assert sessions, "expected at least one session from local fixture"
    session = sessions[0]
    # LocalAdapter delegates to VSCodeAdapter for the VS Code JSONL fixture
    assert session.source == "vscode", f"unexpected source: {session.source}"
    assert session.model, "model should be non-empty"
    assert len(session.messages) >= 2, "expected user + assistant turns"
    assert session.messages[0].role == "user"
    assert session.messages[1].role == "assistant"

    print(
        f"LocalAdapter (auto-detected '{session.source}'): parsed {len(sessions)} session(s)"
    )
    for s in sessions:
        print(f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)}")


if __name__ == "__main__":
    main()
