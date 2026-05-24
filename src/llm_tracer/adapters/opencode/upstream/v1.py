"""OpenCode JSON session and message upstream format types – version 1.

OpenCode stored sessions and messages as separate JSON files under
``$XDG_DATA_HOME/opencode/storage/`` in its pre-SQLite format.

Session file schema::

    title   – session title (string)
    slug    – URL-friendly slug
    version – opencode version string
    time    – {"created": <epoch_ms>, "updated": <epoch_ms>}

Message file schema (v1 — parts inline)::

    id       – message ID
    role     – "user" | "assistant"
    parts    – list of {"type": "text", "text": "..."}
    metadata – {
        "sessionID": "<session file stem>",
        "time":      {"created": <epoch_ms>, "completed": <epoch_ms>},
        "assistant": {"modelID": "...", "providerID": "..."}  (assistant only)
    }

``OpenCodeSessionStateV1`` bundles a session and its messages together as the
state object for the bidirectional lens.

Current version: 1
"""

from typing import NotRequired, TypedDict

"""Public symbols exported by this module."""
__all__ = (
    "OpenCodeAssistantMetadataV1",
    "OpenCodeContentPartV1",
    "OpenCodeMessageDataV1",
    "OpenCodeMessageMetadataV1",
    "OpenCodeMessageTimeV1",
    "OpenCodeSessionDataV1",
    "OpenCodeSessionStateV1",
    "OpenCodeTimeV1",
)


class OpenCodeTimeV1(TypedDict):
    """Time metadata attached to a session."""

    created: NotRequired[int | float]
    updated: NotRequired[int | float]


class OpenCodeSessionDataV1(TypedDict):
    """Parsed payload of a single OpenCode session JSON file."""

    title: NotRequired[str | None]
    slug: NotRequired[str]
    version: NotRequired[str]
    time: NotRequired[OpenCodeTimeV1]


class OpenCodeAssistantMetadataV1(TypedDict):
    """Assistant-specific metadata on a message."""

    modelID: NotRequired[str]
    providerID: NotRequired[str]


class OpenCodeMessageTimeV1(TypedDict):
    """Time metadata attached to a message."""

    created: NotRequired[int | float]
    completed: NotRequired[int | float]


class OpenCodeMessageMetadataV1(TypedDict):
    """Metadata object inside a message file."""

    sessionID: NotRequired[str]
    time: NotRequired[OpenCodeMessageTimeV1]
    assistant: NotRequired[OpenCodeAssistantMetadataV1]


class OpenCodeContentPartV1(TypedDict):
    """One content part within a message."""

    type: str
    text: NotRequired[str]


class OpenCodeMessageDataV1(TypedDict):
    """Parsed payload of a single OpenCode message JSON file."""

    id: NotRequired[str]
    role: str
    parts: NotRequired[list[OpenCodeContentPartV1]]
    metadata: NotRequired[OpenCodeMessageMetadataV1]


class OpenCodeSessionStateV1(TypedDict):
    """Bundled state object for the bidirectional lens.

    Groups a session file with its associated messages so both halves of the
    lens have access to all data needed to build a ``ChatSessionV1``.
    """

    session_id: str
    source_path: str
    session: OpenCodeSessionDataV1
    messages: list[OpenCodeMessageDataV1]
