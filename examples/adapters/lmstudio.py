"""Demo: ingest LM Studio fixture conversations with ``LMStudioAdapter``."""

from pathlib import Path

from examples.adapters._common import verify_against_expected
from llm_tracer.adapters.lmstudio import LMStudioAdapter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "lmstudio" / "conversations"
EXPECTED_JSON = FIXTURE_DIR.parent / "expected.json"


def main() -> None:
    """Ingest the LM Studio fixture and assert expected session structure."""
    adapter = LMStudioAdapter()
    sessions = adapter.ingest(FIXTURE_DIR, ["**/*.json", "**/*.jsonl"])

    assert sessions, "expected at least one session from LM Studio fixture"
    session = sessions[0]
    assert session.source == "lmstudio", f"unexpected source: {session.source}"
    assert session.model, "model should be non-empty"
    assert len(session.messages) == 6, (
        f"expected 6 messages (3 turns x 2), got {len(session.messages)}"
    )
    assert session.messages[0].role == "user"
    assert session.messages[1].role == "assistant"
    assert "import/workspace/python-tutorials" in session.tags, "missing workspace tag"

    verify_against_expected(sessions, EXPECTED_JSON)

    print(f"LMStudioAdapter: parsed {len(sessions)} session(s)")
    for s in sessions:
        print(f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)}")


if __name__ == "__main__":
    main()
