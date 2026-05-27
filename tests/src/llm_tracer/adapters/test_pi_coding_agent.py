"""Unit tests for `llm_tracer.adapters.pi_coding_agent`."""

import json
from pathlib import Path

from llm_tracer.adapters.pi_coding_agent import PiCodingAgentAdapter

"""Public symbols exported by this test module (none)."""
__all__ = ()


def test_pi_coding_agent_default_root_uses_dot_pi_agent_home() -> None:
    """The adapter default root should point at `~/.pi/agent`."""

    adapter = PiCodingAgentAdapter()

    assert adapter.default_roots(options={}) == [Path.home() / ".pi" / "agent"]


def test_pi_coding_agent_ingests_jsonl_event_stream(tmp_path: Path) -> None:
    """The adapter should parse `.pi/agent/sessions/*/*.jsonl` event streams."""

    root = tmp_path / ".pi" / "agent"
    session_dir = root / "sessions" / "project-1"
    session_dir.mkdir(parents=True)
    session_path = session_dir / "session-1.jsonl"
    rows = [
        {
            "type": "session",
            "id": "sess-1",
            "timestamp": "2026-05-24T06:18:37.619Z",
        },
        {
            "type": "model_change",
            "id": "m-1",
            "modelId": "moonshotai/Kimi-K2.6",
        },
        {
            "type": "message",
            "id": "u-1",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "hello"}],
            },
        },
        {
            "type": "message",
            "id": "a-1",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "world"}],
            },
        },
    ]
    session_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    adapter = PiCodingAgentAdapter()
    sessions = adapter.ingest(root, ["**/*.jsonl"])

    assert len(sessions) == 1
    session = sessions[0]
    assert session.source == "pi_coding_agent"
    assert session.source_record_id == "sess-1"
    assert session.model == "moonshotai/Kimi-K2.6"
    assert [message.role for message in session.messages] == ["user", "assistant"]
    assert [message.content for message in session.messages] == ["hello", "world"]
