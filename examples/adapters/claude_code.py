"""Demo: ingest a Claude Code transcript JSONL file."""

from pathlib import Path

from examples.adapters._common import verify_against_expected
from llm_tracer.adapters.claude_code import ClaudeCodeAdapter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "claude_code" / "projects"
EXPECTED_JSON = FIXTURE_DIR.parent / "expected.json"


def main() -> None:
    """Ingest fixture transcripts and assert expected normalized structure."""
    adapter = ClaudeCodeAdapter()
    sessions = adapter.ingest(FIXTURE_DIR, ["**/*.jsonl"])

    assert sessions, "expected at least one Claude Code session"
    session = sessions[0]
    assert session.source == "claude_code"
    assert session.model == "claude-sonnet-4.5"
    assert [message.role for message in session.messages] == ["user", "assistant"]

    verify_against_expected(sessions, EXPECTED_JSON)

    print(f"ClaudeCodeAdapter: parsed {len(sessions)} session(s)")
    for s in sessions:
        print(f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)}")


if __name__ == "__main__":
    main()
