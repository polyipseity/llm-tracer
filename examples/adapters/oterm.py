"""Demo: ingest oterm chats from a SQLite store.db fixture."""

import os
from pathlib import Path

from examples.adapters._common import verify_against_expected
from llm_tracer.adapters.oterm import OTermAdapter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "oterm"
EXPECTED_JSON = FIXTURE_DIR / "expected.json"


def main() -> None:
    """Ingest the oterm SQLite fixture and verify normalized output."""
    # Ensure deterministic epoch 0 timestamp (oterm uses mtime, which varies)
    os.utime(FIXTURE_DIR / "store.db", (0, 0))

    adapter = OTermAdapter()
    sessions = adapter.ingest(FIXTURE_DIR, ["**/*.db"])

    assert sessions, "expected at least one oterm session"
    session = sessions[0]
    assert session.source == "oterm"
    assert session.model == "llama3.1"
    assert [message.role for message in session.messages] == ["user", "assistant"]

    verify_against_expected(
        sessions, EXPECTED_JSON, skip_fields=["ingest_key", "timestamp"]
    )

    print(f"OTermAdapter: parsed {len(sessions)} session(s)")
    for s in sessions:
        print(f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)}")


if __name__ == "__main__":
    main()
