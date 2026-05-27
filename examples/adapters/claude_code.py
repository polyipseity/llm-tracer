"""Demo: ingest a Claude Code transcript JSONL file."""

from pathlib import Path

from llm_tracer.adapters.claude_code import ClaudeCodeAdapter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "claude_code" / "projects"


def main() -> None:
    """Ingest fixture transcripts and assert expected normalized structure."""
    adapter = ClaudeCodeAdapter()
    sessions = adapter.ingest(FIXTURE_DIR, ["**/*.jsonl"])

    assert sessions, "expected at least one Claude Code session"
    session = sessions[0]
    assert session.source == "claude_code"
    assert session.model == "claude-sonnet-4.5"
    assert [message.role for message in session.messages] == ["user", "assistant"]


if __name__ == "__main__":
    main()
