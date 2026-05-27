"""Demo: ingest oterm chats from a SQLite store.db fixture."""

import json as _json
import os
from pathlib import Path

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

    _expected = _json.loads(EXPECTED_JSON.read_text(encoding="utf-8"))
    _actual = [s.model_dump(mode="json") for s in sessions]
    for _d in _actual + _expected:
        _d.pop("ingest_key", None)
        _d.pop("timestamp", None)  # mtime-based, skip comparison
    assert _actual == _expected, "session output does not match expected.json"

    print(f"OTermAdapter: parsed {len(sessions)} session(s)")
    for s in sessions:
        print(f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)}")


if __name__ == "__main__":
    main()
