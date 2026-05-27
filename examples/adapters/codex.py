"""Demo: ingest a Codex rollout JSONL file."""

from pathlib import Path

from llm_tracer.adapters.codex import CodexAdapter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "codex" / "sessions"


def main() -> None:
    """Ingest fixture rollouts and assert expected normalized structure."""
    adapter = CodexAdapter()
    sessions = adapter.ingest(FIXTURE_DIR, ["**/*.jsonl"])

    assert sessions, "expected at least one Codex session"
    session = sessions[0]
    assert session.source == "codex"
    assert session.model == "gpt-5-codex"
    assert [message.role for message in session.messages] == ["user", "assistant"]


if __name__ == "__main__":
    main()
