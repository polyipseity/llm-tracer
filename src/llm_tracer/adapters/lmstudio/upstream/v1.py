"""LM Studio conversation upstream format types – version 1.

LM Studio stores conversations as JSON files.  The upstream format is the
parsed JSON payload of a single ``.conversation.json`` file.

Each message in LM Studio is a "turn container" with a ``versions`` list
(supporting edits/regenerations).  The adapter uses ``currentlySelected``
to pick the active version.

Future format versions will be defined in ``v2.py``, ``v3.py``, …

Current version: 1
"""

from typing import Any, NotRequired, TypedDict

"""Public symbols exported by this module."""
__all__ = (
    "LMStudioContentPartV1",
    "LMStudioConversationV1",
    "LMStudioPreprocessedV1",
    "LMStudioTurnV1",
    "LMStudioVersionV1",
)


class LMStudioContentPartV1(TypedDict):
    """One content part within a message version."""

    type: str
    text: NotRequired[str]


class LMStudioPreprocessedV1(TypedDict):
    """Preprocessing metadata attached to a message version."""

    timestamp: NotRequired[int]


class LMStudioVersionV1(TypedDict):
    """One version of a message turn (edit/regeneration)."""

    role: str
    content: NotRequired[list[LMStudioContentPartV1] | str]
    preprocessed: NotRequired[LMStudioPreprocessedV1]
    steps: NotRequired[list[Any]]


class LMStudioTurnV1(TypedDict):
    """A turn container holding one or more message versions."""

    versions: list[LMStudioVersionV1]
    currentlySelected: NotRequired[int]


class LMStudioConversationV1(TypedDict):
    """The parsed payload of a single LM Studio .conversation.json file."""

    name: NotRequired[str | None]
    title: NotRequired[str | None]
    createdAt: NotRequired[int | None]
    model: NotRequired[str | None]
    messages: NotRequired[list[LMStudioTurnV1]]
    conversation: NotRequired[list[LMStudioTurnV1]]
    tags: NotRequired[list[Any]]
    systemPrompt: NotRequired[str]
    pinned: NotRequired[bool]
    tokenCount: NotRequired[int]
