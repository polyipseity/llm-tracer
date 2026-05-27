"""Claude Code transcript event types – 2026-01 format.

The format is newline-delimited JSON objects captured in
`~/.claude/projects/<project>/<session>.jsonl`.
"""

from typing import NotRequired, TypedDict

"""Public symbols exported by this module."""
__all__ = (
    "ClaudeCodeContentPartV2026_01",
    "ClaudeCodeEventV2026_01",
    "ClaudeCodeMessageV2026_01",
)


class ClaudeCodeContentPartV2026_01(TypedDict):
    """One item in a Claude message content list."""

    type: NotRequired[str]
    text: NotRequired[str]


class ClaudeCodeMessageV2026_01(TypedDict):
    """Embedded message object in a Claude transcript event."""

    role: NotRequired[str]
    content: NotRequired[str | list[ClaudeCodeContentPartV2026_01]]
    id: NotRequired[str]
    model: NotRequired[str]


class ClaudeCodeEventV2026_01(TypedDict):
    """One JSONL event row in a Claude transcript."""

    type: NotRequired[str]
    timestamp: NotRequired[str]
    uuid: NotRequired[str]
    sessionId: NotRequired[str]
    message: NotRequired[ClaudeCodeMessageV2026_01]
