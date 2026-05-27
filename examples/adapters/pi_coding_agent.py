"""Demo: ingest a PI Coding Agent execution trace using PiCodingAgentAdapter.

PI Coding Agent is the agentic coding assistant from Inflection AI
(https://pi.ai). No public documentation of its trace file format exists;
this adapter was written by reverse-engineering traces captured from local
executions.

The adapter recognises these top-level fields:

- Timestamp: ``timestamp`` or ``started_at`` (ISO 8601 string)
- Messages: ``messages``, ``events``, or ``steps`` (list of turn dicts with
  ``role`` and ``content``)
- Model: ``model`` or ``agent_model``
- ID: ``trace_id``, ``id``, or ``run_id``
- Title: ``title`` or ``name``

The fixture uses the ``trace_id`` + ``steps`` variant to exercise the
alternative field names.

Sources
-------
- PI Coding Agent: https://pi.ai (no public trace format documentation)
- Adapter implementation:
  ``src/llm_tracer/adapters/pi_coding_agent.py``
"""

import json as _json
from pathlib import Path

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

    _expected = _json.loads(EXPECTED_JSON.read_text(encoding="utf-8"))
    _actual = [s.model_dump(mode="json") for s in sessions]
    for _d in _actual + _expected:
        _d.pop("ingest_key", None)
    assert _actual == _expected, "session output does not match expected.json"

    print(f"PiCodingAgentAdapter: parsed {len(sessions)} session(s)")
    for s in sessions:
        print(f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)}")


if __name__ == "__main__":
    main()
