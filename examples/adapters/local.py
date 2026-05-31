"""Demo: ingest local fixtures with ``LocalAdapter`` auto-detection."""

from pathlib import Path

from examples.adapters._common import verify_against_expected
from llm_tracer.adapters.local import LocalAdapter

# Fixture root for LocalAdapter — the top-level local fixture directory.
FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "local" / "workspaceStorage"
EXPECTED_JSON = FIXTURE_DIR.parent / "expected.json"


def main() -> None:
    """Ingest the local JSONL fixture and assert auto-detected session structure."""
    adapter = LocalAdapter()
    sessions = adapter.ingest(FIXTURE_DIR, ["**/*.json", "**/*.jsonl"])

    assert sessions, "expected at least one session from local fixture"
    # Filter for vscode sessions — expected.json may also be parsed by other adapters
    vscode_sessions = [s for s in sessions if s.source == "vscode"]
    assert vscode_sessions, "expected at least one auto-detected vscode session"
    session = vscode_sessions[0]
    assert session.model, "model should be non-empty"
    assert len(session.messages) >= 4, "expected 2 user + 2 assistant turns"
    assert session.messages[0].role == "user"
    assert session.messages[1].role == "assistant"

    verify_against_expected(sessions, EXPECTED_JSON)

    print(
        f"LocalAdapter (auto-detected '{session.source}'): parsed {len(sessions)} session(s)"
    )
    for s in sessions:
        print(f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)}")


if __name__ == "__main__":
    main()
