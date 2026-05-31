"""Demo: ingest an LM Studio conversation using LMStudioAdapter.

LM Studio stores conversations in JSON format at
``~/.lmstudio/conversations/<subfolder>/<epoch-ms>.conversation.json``
on all platforms — Mac, Linux, and Windows (``~`` = ``%USERPROFILE%``
on Windows). Source: https://lmstudio.ai/docs/app/basics/chat
The filename's epoch-ms prefix is the conversation identifier — there is
no ``id`` field inside the JSON.

Real format top-level fields: ``name`` (title), ``createdAt`` (epoch ms
integer), ``tokenCount``, ``systemPrompt``, ``messages``. Each message
entry uses a versioned structure: ``{"versions": [...], "currentlySelected": 0}``,
where each version has ``role``, ``content`` (structured parts array), and
optionally ``steps`` with ``genInfo.indexedModelIdentifier`` for the model.

Sources
-------
- LM Studio chat docs: https://lmstudio.ai/docs/app/basics/chat
- Official SDK type definitions:
  https://github.com/lmstudio-ai/lmstudio-js/blob/main/packages/lms-shared-types/src/ChatHistoryData.ts
- Real-file parser confirming versioned schema:
  https://github.com/skiretic/lmstudiochatconverter
"""

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
