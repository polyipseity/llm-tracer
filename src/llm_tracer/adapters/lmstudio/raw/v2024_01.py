"""LM Studio conversation upstream format types – 2024-01 format.

LM Studio stores conversations as JSON files.  The upstream format is the
parsed JSON payload of a single ``.conversation.json`` file.

The 2024-01 format is date-based; there is no explicit version field in the
data.  This format predates LM Studio 0.3.x.

Each message in LM Studio is a "turn container" with a ``versions`` list
(supporting edits/regenerations).  The adapter uses ``currentlySelected``
to pick the active version.

Future format versions will be defined in ``v2025_01.py``, …

Current version: 2024_01
"""

from typing import Any, NotRequired, TypedDict

"""Public symbols exported by this module."""
__all__ = (
    "LMStudioContentPartV2024_01",
    "LMStudioConversationV2024_01",
    "LMStudioPreprocessedV2024_01",
    "LMStudioTurnV2024_01",
    "LMStudioVersionV2024_01",
)


class LMStudioContentPartV2024_01(TypedDict):
    """One content part within a message version."""

    type: str
    text: NotRequired[str]


class LMStudioPreprocessedV2024_01(TypedDict):
    """Preprocessing metadata attached to a message version."""

    timestamp: NotRequired[int]


class LMStudioVersionV2024_01(TypedDict):
    """One version of a message turn (edit/regeneration)."""

    role: str
    content: NotRequired[list[LMStudioContentPartV2024_01] | str]
    preprocessed: NotRequired[LMStudioPreprocessedV2024_01]
    steps: NotRequired[list[Any]]


class LMStudioTurnV2024_01(TypedDict):
    """A turn container holding one or more message versions."""

    versions: list[LMStudioVersionV2024_01]
    currentlySelected: NotRequired[int]


class LMStudioConversationV2024_01(TypedDict):
    """The parsed payload of a single LM Studio .conversation.json file."""

    name: NotRequired[str | None]
    title: NotRequired[str | None]
    createdAt: NotRequired[int | None]
    model: NotRequired[str | None]
    messages: NotRequired[list[LMStudioTurnV2024_01]]
    conversation: NotRequired[list[LMStudioTurnV2024_01]]
    tags: NotRequired[list[Any]]
    systemPrompt: NotRequired[str]
    pinned: NotRequired[bool]
    tokenCount: NotRequired[int]
