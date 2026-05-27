"""Demo: ingest a session using LocalAdapter (auto-detection).

``LocalAdapter`` wraps all concrete adapters — ``VSCodeAdapter``,
``PiCodingAgentAdapter``, ``LMStudioAdapter``, ``OpenCodeAdapter`` — and
tries each in turn, returning the result of the first adapter that succeeds.

The fixture here is a VS Code Copilot Chat JSONL mutation log stored in a
realistic directory tree:
``workspaceStorage/{32-hex-hash}/chatSessions/{session-uuid}.jsonl``.
``LocalAdapter`` detects it via ``VSCodeAdapter`` and normalises it with
``source = "vscode"``, demonstrating transparent auto-detection.

Note: because ``LocalAdapter`` calls
``delegate.ingest(source_path.parent, [source_path.name])``, the root passed
to VSCodeAdapter is the ``chatSessions/`` directory.  With only one path part
relative to that root, no ``workspace_id`` tag is emitted — this is by design.

Sources
-------
- VS Code JSONL format: https://github.com/digitarald/vscode-session-trace/blob/main/src/types.ts
- LocalAdapter delegation order: ``src/llm_tracer/adapters/local.py``
"""

import json as _json
from pathlib import Path

from llm_tracer.adapters.local import LocalAdapter

"Fixture root for LocalAdapter — the top-level local fixture directory."
FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "local" / "workspaceStorage"
EXPECTED_JSON = FIXTURE_DIR.parent / "expected.json"


def main() -> None:
    """Ingest the local JSONL fixture and assert auto-detected session structure."""
    adapter = LocalAdapter()
    sessions = adapter.ingest(FIXTURE_DIR, ["**/*.json", "**/*.jsonl"])

    assert sessions, "expected at least one session from local fixture"
    # Filter for vscode sessions — expected.json may also be parsed by other adapters
    vscode_sessions = [s for s in sessions if s.source == "vscode"]
    assert vscode_sessions, "expected at least one auto-detected vscode session"
    session = vscode_sessions[0]
    assert session.model, "model should be non-empty"
    assert len(session.messages) >= 4, "expected 2 user + 2 assistant turns"
    assert session.messages[0].role == "user"
    assert session.messages[1].role == "assistant"

    _expected = _json.loads(EXPECTED_JSON.read_text(encoding="utf-8"))
    _actual = [s.model_dump(mode="json") for s in sessions]
    for _d in _actual + _expected:
        _d.pop("ingest_key", None)
    assert _actual == _expected, "session output does not match expected.json"

    print(
        f"LocalAdapter (auto-detected '{session.source}'): parsed {len(sessions)} session(s)"
    )
    for s in sessions:
        print(f"  id={s.id[:8]}... model={s.model!r} msgs={len(s.messages)}")


if __name__ == "__main__":
    main()
