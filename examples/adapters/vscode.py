"""Demo: ingest VS Code fixture sessions with ``VSCodeAdapter``."""

from pathlib import Path

from examples.adapters._common import verify_against_expected
from llm_tracer.adapters.vscode import VSCodeAdapter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "vscode" / "workspaceStorage"
EXPECTED_JSON = FIXTURE_DIR.parent / "expected.json"


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

    assert "import/workspace/llm-tracer" in session.tags, (
        f"missing import/workspace/llm-tracer tag; got: {session.tags}"
    )

    verify_against_expected(sessions, EXPECTED_JSON)

    print(f"VSCodeAdapter: parsed {len(sessions)} session(s)")
    for s in sessions:
        print(
            f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)} tags={s.tags}"
        )


if __name__ == "__main__":
    main()
