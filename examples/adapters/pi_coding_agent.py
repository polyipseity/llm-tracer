"""Demo: ingest PI Coding Agent fixture traces with ``PiCodingAgentAdapter``."""

from pathlib import Path

from examples.adapters._common import verify_against_expected
from llm_tracer.adapters.pi_coding_agent import PiCodingAgentAdapter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "pi_coding_agent" / "sessions"
EXPECTED_JSON = FIXTURE_DIR.parent / "expected.json"


def main() -> None:
    """Ingest the PI Coding Agent fixture and assert expected session structure."""
    adapter = PiCodingAgentAdapter()
    sessions = adapter.ingest(FIXTURE_DIR, ["**/*.json", "**/*.jsonl"])

    assert sessions, "expected at least one session from PI Coding Agent fixture"
    session = sessions[0]
    assert session.source == "pi_coding_agent", f"unexpected source: {session.source}"
    assert session.model, "model should be non-empty"
    assert len(session.messages) == 6, (
        f"expected 6 messages (3 user + 3 assistant turns), got {len(session.messages)}"
    )
    assert session.messages[0].role == "user"
    assert session.messages[1].role == "assistant"
    assert any("pi_coding_agent" in tag for tag in session.tags), (
        "missing pi_coding_agent id tag"
    )

    verify_against_expected(sessions, EXPECTED_JSON)

    print(f"PiCodingAgentAdapter: parsed {len(sessions)} session(s)")
    for s in sessions:
        print(f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)}")


if __name__ == "__main__":
    main()
