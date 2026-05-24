"""VS Code Copilot Chat upstream format types – version 3.

Version 3 covers the JSONL mutation-log format introduced in VS Code ≥ 1.109 /
github.copilot-chat ≥ 0.47.0 (released February 2026).

The upstream state for one chat session is the result of replaying all JSONL
mutation entries: a ``VSCodeSessionStateV3`` dict.  The replayed state carries
an explicit ``version`` integer field whose value is ``3``.

Future format versions will be defined in ``v4.py``, ``v5.py``, … Each
adjacent pair has a bidirectional ``Iso`` lens in ``v{n}_to_v{n+1}.py``::

    from lenses import bind
    v4_state = bind(v3_state).Iso(v3_to_v4_func, v4_to_v3_func).get()

Current version: 3
"""

from typing import Any, NotRequired, TypedDict

"""Public symbols exported by this module."""
__all__ = (
    "VSCodeMessagePayloadV3",
    "VSCodeRequestV3",
    "VSCodeResponsePartV3",
    "VSCodeSessionStateV3",
)


class VSCodeResponsePartV3(TypedDict):
    """One response part in a VS Code Copilot Chat request."""

    kind: str
    content: NotRequired[str]


class VSCodeMessagePayloadV3(TypedDict):
    """The user message payload of a VS Code Copilot Chat request."""

    text: str
    parts: NotRequired[list[Any]]


class VSCodeRequestV3(TypedDict):
    """A single request-response pair in a VS Code Copilot Chat session."""

    requestId: str
    timestamp: NotRequired[int]
    modelId: NotRequired[str]
    message: NotRequired[VSCodeMessagePayloadV3]
    response: NotRequired[list[VSCodeResponsePartV3]]
    completionTokens: NotRequired[int]


class VSCodeSessionStateV3(TypedDict):
    """The fully-replayed state of a VS Code Copilot Chat JSONL session file."""

    sessionId: str
    creationDate: int
    version: NotRequired[int]
    customTitle: NotRequired[str | None]
    requests: NotRequired[list[VSCodeRequestV3]]
