"""Demo: ingest a Claude Code transcript JSONL file."""

import json as _json
from pathlib import Path

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

    _expected = _json.loads(EXPECTED_JSON.read_text(encoding="utf-8"))
    _actual = [s.model_dump(mode="json") for s in sessions]
    for _d in _actual + _expected:
        _d.pop("ingest_key", None)
    assert _actual == _expected, "session output does not match expected.json"

    print(f"ClaudeCodeAdapter: parsed {len(sessions)} session(s)")
    for s in sessions:
        print(f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)}")


if __name__ == "__main__":
    main()
