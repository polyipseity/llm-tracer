"""Demo: ingest Ollama CLI prompt history."""

from pathlib import Path

from llm_tracer.adapters.ollama import OllamaAdapter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "ollama"


def main() -> None:
    """Ingest fixture prompt history and assert normalized prompt-only sessions."""
    adapter = OllamaAdapter()
    sessions = adapter.ingest(FIXTURE_DIR, ["**/*"])

    assert sessions, "expected at least one Ollama prompt session"
    assert all(session.source == "ollama" for session in sessions)
    assert all(session.messages[0].role == "user" for session in sessions)


if __name__ == "__main__":
    main()
