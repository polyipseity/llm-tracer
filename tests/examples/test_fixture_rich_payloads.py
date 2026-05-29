"""Validate that example fixtures include rich non-text payload coverage."""

from pathlib import Path

import pytest

"""Public symbols exported by this test module (none)."""
__all__ = ()

"""Repository root used to resolve fixture paths."""
_REPO_ROOT = Path(__file__).parent.parent.parent

"""Fixture files and required marker substrings that indicate rich payloads."""
_FIXTURE_MARKERS: tuple[tuple[Path, tuple[str, ...]], ...] = (
    (
        _REPO_ROOT
        / "examples/fixtures/vscode/workspaceStorage/baed92910affe51bce3aeb07d38a7955/chatSessions/03188b43-d8b5-429c-8b70-2cb2ecc29620.jsonl",
        ('"kind":"image"', '"kind":"attachment"', '"kind":"embedding"'),
    ),
    (
        _REPO_ROOT
        / "examples/fixtures/local/workspaceStorage/da3e6382abc1234567890abcdef01234/chatSessions/b1c2d3e4-0001-0001-0001-000000000001.jsonl",
        ('"kind":"image"', '"kind":"attachment"', '"kind":"embedding"'),
    ),
    (
        _REPO_ROOT
        / "examples/fixtures/lmstudio/conversations/python-tutorials/1737000000000.conversation.json",
        ('"type": "image"', '"type": "embedding"', '"type": "attachment"'),
    ),
    (
        _REPO_ROOT
        / "examples/fixtures/opencode/storage/message/session_001/msg_001.json",
        ('"type": "attachment"', '"embeddings"'),
    ),
    (
        _REPO_ROOT
        / "examples/fixtures/opencode/storage/message/session_001/msg_002.json",
        ('"type": "image"', '"embeddings"'),
    ),
    (
        _REPO_ROOT
        / "examples/fixtures/opencode/storage/message/session_001/msg_004.json",
        ('"type": "embedding"', '"attachments"'),
    ),
    (
        _REPO_ROOT
        / "examples/fixtures/claude_code/projects/example-project/example-session.jsonl",
        ('"type":"image"', '"embeddings"', '"attachments"'),
    ),
    (
        _REPO_ROOT
        / "examples/fixtures/codex/sessions/2026/05/27/rollout-2026-05-27T10-00-00-test.jsonl",
        ('"type":"image"', '"embeddings"', '"attachments"'),
    ),
    (
        _REPO_ROOT / "examples/fixtures/pi_coding_agent/sessions/trace.json",
        ('"attachments"', '"embedding"', '"embeddings"'),
    ),
    (
        _REPO_ROOT / "examples/fixtures/ollama/history",
        ("![model list screenshot]", "embedding=["),
    ),
    (
        _REPO_ROOT / "examples/fixtures/oterm/expected.json",
        ("attachment:", "embedding=["),
    ),
)


def _read_fixture(path: Path) -> str:
    """Read a fixture file as UTF-8 text."""
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize(("path", "markers"), _FIXTURE_MARKERS)
def test_fixtures_include_rich_payload_markers(
    path: Path, markers: tuple[str, ...]
) -> None:
    """Ensure each fixture includes representative non-text payload markers."""
    content = _read_fixture(path)
    for marker in markers:
        assert marker in content
