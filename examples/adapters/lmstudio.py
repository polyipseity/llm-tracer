"""Demo: ingest an LM Studio conversation using LMStudioAdapter.

LM Studio stores conversations in JSON format under
``~/.lmstudio/conversations/`` on macOS/Linux, and
``%USERPROFILE%\\.lmstudio\\conversations\\`` on Windows (source:
https://lmstudio.ai/docs/app/basics/chat). The LM Studio documentation
explicitly notes that the conversation structure is **not recommended to rely
on**, so no stable schema is publicly documented.

The fixture here uses a simplified format aligned with the fields
``LMStudioAdapter`` parses: ``id``, ``timestamp`` (ISO string), ``model``,
``title``, and a ``messages`` array of ``{role, content}`` objects. LM Studio's
SDK defines messages with structured ``content`` arrays (see
``ChatHistoryData.ts`` in
https://github.com/lmstudio-ai/lmstudio-js), but the on-disk flat-string
format matches common LLM chat export conventions.

Sources
-------
- LM Studio chat documentation: https://lmstudio.ai/docs/app/basics/chat
- LM Studio JS SDK types:
  https://github.com/lmstudio-ai/lmstudio-js/blob/main/packages/lms-shared-types/src/ChatHistoryData.ts
"""

from pathlib import Path

from llm_tracer.adapters.lmstudio import LMStudioAdapter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "lmstudio"


def main() -> None:
    """Ingest the LM Studio fixture and assert expected session structure."""
    adapter = LMStudioAdapter()
    sessions = adapter.ingest(FIXTURE_DIR, ["**/*.json", "**/*.jsonl"])

    assert sessions, "expected at least one session from LM Studio fixture"
    session = sessions[0]
    assert session.source == "lmstudio", f"unexpected source: {session.source}"
    assert session.model, "model should be non-empty"
    assert len(session.messages) >= 2, "expected user + assistant turns"
    assert session.messages[0].role == "user"
    assert session.messages[1].role == "assistant"
    assert any("lmstudio" in tag for tag in session.tags), "missing lmstudio id tag"

    print(f"LMStudioAdapter: parsed {len(sessions)} session(s)")
    for s in sessions:
        print(f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)}")


if __name__ == "__main__":
    main()
