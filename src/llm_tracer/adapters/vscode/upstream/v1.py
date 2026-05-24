"""VS Code Copilot Chat upstream format types – version 1.

Version 1 covers the JSONL mutation-log format introduced in VS Code ≥ 1.109 /
github.copilot-chat ≥ 0.47.0 (released February 2026).

The upstream state for one chat session is the result of replaying all JSONL
mutation entries: a ``VSCodeSessionStateV1`` dict.

Future format versions will be defined in ``v2.py``, ``v3.py``, … Each
adjacent pair has a bidirectional ``Iso`` lens in ``v{n}_to_v{n+1}.py``::

    from lenses import bind
    v2_state = bind(v1_state).Iso(v1_to_v2_func, v2_to_v1_func).get()

Current version: 1
"""

from typing import Any, NotRequired, TypedDict

"""Public symbols exported by this module."""
__all__ = (
    "VSCodeMessagePayloadV1",
    "VSCodeRequestV1",
    "VSCodeResponsePartV1",
    "VSCodeSessionStateV1",
)


class VSCodeResponsePartV1(TypedDict):
    """One response part in a VS Code Copilot Chat request."""

    kind: str
    content: NotRequired[str]


class VSCodeMessagePayloadV1(TypedDict):
    """The user message payload of a VS Code Copilot Chat request."""

    text: str
    parts: NotRequired[list[Any]]


class VSCodeRequestV1(TypedDict):
    """A single request-response pair in a VS Code Copilot Chat session."""

    requestId: str
    timestamp: NotRequired[int]
    modelId: NotRequired[str]
    message: NotRequired[VSCodeMessagePayloadV1]
    response: NotRequired[list[VSCodeResponsePartV1]]
    completionTokens: NotRequired[int]


class VSCodeSessionStateV1(TypedDict):
    """The fully-replayed state of a VS Code Copilot Chat JSONL session file."""

    sessionId: str
    creationDate: int
    customTitle: NotRequired[str | None]
    requests: NotRequired[list[VSCodeRequestV1]]
