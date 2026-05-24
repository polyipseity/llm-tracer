"""OpenCode JSON session and message upstream format types – 2025-01 format.

OpenCode stored sessions and messages as separate JSON files under
``$XDG_DATA_HOME/opencode/storage/`` in its pre-SQLite format.

The 2025-01 format is date-based.  Note that the ``version`` field in OpenCode
JSON is the application semver string, not a schema version discriminator.

Session file schema::

    title   – session title (string)
    slug    – URL-friendly slug
    version – opencode app version string (semver, not a schema discriminator)
    time    – {"created": <epoch_ms>, "updated": <epoch_ms>}

Message file schema (2025-01 — parts inline)::

    id       – message ID
    role     – "user" | "assistant"
    parts    – list of {"type": "text", "text": "..."}
    metadata – {
        "sessionID": "<session file stem>",
        "time":      {"created": <epoch_ms>, "completed": <epoch_ms>},
        "assistant": {"modelID": "...", "providerID": "..."}  (assistant only)
    }

``OpenCodeSessionStateV2025_01`` bundles a session and its messages together as
the state object for the bidirectional lens.

Current version: 2025_01
"""

from typing import NotRequired, TypedDict

"""Public symbols exported by this module."""
__all__ = (
    "OpenCodeAssistantMetadataV2025_01",
    "OpenCodeContentPartV2025_01",
    "OpenCodeMessageDataV2025_01",
    "OpenCodeMessageMetadataV2025_01",
    "OpenCodeMessageTimeV2025_01",
    "OpenCodeSessionDataV2025_01",
    "OpenCodeSessionStateV2025_01",
    "OpenCodeTimeV2025_01",
)


class OpenCodeTimeV2025_01(TypedDict):
    """Time metadata attached to a session."""

    created: NotRequired[int | float]
    updated: NotRequired[int | float]


class OpenCodeSessionDataV2025_01(TypedDict):
    """Parsed payload of a single OpenCode session JSON file."""

    title: NotRequired[str | None]
    slug: NotRequired[str]
    version: NotRequired[str]
    time: NotRequired[OpenCodeTimeV2025_01]


class OpenCodeAssistantMetadataV2025_01(TypedDict):
    """Assistant-specific metadata on a message."""

    modelID: NotRequired[str]
    providerID: NotRequired[str]


class OpenCodeMessageTimeV2025_01(TypedDict):
    """Time metadata attached to a message."""

    created: NotRequired[int | float]
    completed: NotRequired[int | float]


class OpenCodeMessageMetadataV2025_01(TypedDict):
    """Metadata object inside a message file."""

    sessionID: NotRequired[str]
    time: NotRequired[OpenCodeMessageTimeV2025_01]
    assistant: NotRequired[OpenCodeAssistantMetadataV2025_01]


class OpenCodeContentPartV2025_01(TypedDict):
    """One content part within a message."""

    type: str
    text: NotRequired[str]


class OpenCodeMessageDataV2025_01(TypedDict):
    """Parsed payload of a single OpenCode message JSON file."""

    id: NotRequired[str]
    role: str
    parts: NotRequired[list[OpenCodeContentPartV2025_01]]
    metadata: NotRequired[OpenCodeMessageMetadataV2025_01]


class OpenCodeSessionStateV2025_01(TypedDict):
    """Bundled state object for the bidirectional lens.

    Groups a session file with its associated messages so both halves of the
    lens have access to all data needed to build a ``ChatSessionV1``.
    """

    session_id: str
    source_path: str
    session: OpenCodeSessionDataV2025_01
    messages: list[OpenCodeMessageDataV2025_01]
