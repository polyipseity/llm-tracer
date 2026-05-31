"""Demo: ingest Ollama CLI prompt history."""

import os
from pathlib import Path

from examples.adapters._common import verify_against_expected
from llm_tracer.adapters.ollama import OllamaAdapter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "ollama"
EXPECTED_JSON = FIXTURE_DIR / "expected.json"


def main() -> None:
    """Ingest fixture prompt history and assert normalized prompt-only sessions."""
    # Ensure deterministic epoch 0 timestamp (ollama uses mtime, which varies)
    os.utime(FIXTURE_DIR / "history", (0, 0))

    adapter = OllamaAdapter()
    sessions = adapter.ingest(FIXTURE_DIR, ["**/*"])

    assert sessions, "expected at least one Ollama prompt session"
    assert all(session.source == "ollama" for session in sessions)
    assert all(session.messages[0].role == "user" for session in sessions)

    verify_against_expected(
        sessions, EXPECTED_JSON, skip_fields=["ingest_key", "timestamp"]
    )

    print(f"OllamaAdapter: parsed {len(sessions)} session(s)")
    for s in sessions:
        print(f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)}")


if __name__ == "__main__":
    main()
