"""Codex rollout event types – 2026-01 format.

Codex stores local rollouts as JSONL files under
`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`.
"""

from typing import Any, NotRequired, TypedDict

"""Public symbols exported by this module."""
__all__ = (
    "CodexEventV2026_01",
    "CodexMessageV2026_01",
)


class CodexMessageV2026_01(TypedDict):
    """Embedded message payload in a Codex event row."""

    role: NotRequired[str]
    content: NotRequired[str | list[dict[str, Any]]]
    model: NotRequired[str]


class CodexEventV2026_01(TypedDict):
    """One JSONL row in a Codex rollout file."""

    type: NotRequired[str]
    id: NotRequired[str]
    timestamp: NotRequired[str]
    modelId: NotRequired[str]
    message: NotRequired[CodexMessageV2026_01]
