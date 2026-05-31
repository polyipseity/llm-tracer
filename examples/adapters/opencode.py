"""Demo: ingest OpenCode fixture sessions with ``OpenCodeAdapter``."""

from pathlib import Path

from examples.adapters._common import verify_against_expected
from llm_tracer.adapters.opencode import OpenCodeAdapter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "opencode" / "storage"
EXPECTED_JSON = FIXTURE_DIR.parent / "expected.json"


def main() -> None:
    """Ingest the OpenCode multi-file fixture and assert expected session structure."""
    adapter = OpenCodeAdapter()
    sessions = adapter.ingest(FIXTURE_DIR, ["**/*.json", "**/*.jsonl"])

    assert sessions, "expected at least one session from OpenCode fixture"
    session = sessions[0]
    assert session.source == "opencode", f"unexpected source: {session.source}"
    assert session.model, "model should be non-empty"
    assert len(session.messages) == 4, (
        f"expected 4 messages, got {len(session.messages)}"
    )
    assert session.messages[0].role == "user"
    assert session.messages[1].role == "assistant"
    assert session.messages[2].role == "user"
    assert session.messages[3].role == "assistant"
    assert "import/workspace/llm-tracer" in session.tags, (
        f"missing import/workspace/llm-tracer tag; got: {session.tags}"
    )

    verify_against_expected(sessions, EXPECTED_JSON)

    print(f"OpenCodeAdapter: parsed {len(sessions)} session(s)")
    for s in sessions:
        print(f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)}")


if __name__ == "__main__":
    main()
