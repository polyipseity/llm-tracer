"""OpenCode JSON session and message upstream format types – 2025-05 format.

OpenCode stored sessions and messages as separate JSON files under
``$XDG_DATA_HOME/opencode/storage/`` in its pre-SQLite format.

The 2025-05 format is date-based.  Note that the ``version`` field in OpenCode
JSON is the application semver string, not a schema version discriminator.
OpenCode's first public release was v0.0.45 on 2025-05-15; the JSON storage
format was the original format from launch until the SQLite migration in
approximately February 2026.

Session file schema::

    title   – session title (string)
    slug    – URL-friendly slug
    version – opencode app version string (semver, not a schema discriminator)
    time    – {"created": <epoch_ms>, "updated": <epoch_ms>}

Message file schema (2025-05 — parts inline)::

    id       – message ID
    role     – "user" | "assistant"
    parts    – list of {"type": "text", "text": "..."}
    metadata – {
        "sessionID": "<session file stem>",
        "time":      {"created": <epoch_ms>, "completed": <epoch_ms>},
        "assistant": {"modelID": "...", "providerID": "..."}  (assistant only)
    }

``OpenCodeSessionStateV2025_05`` bundles a session and its messages together as
the state object for the bidirectional lens.

Current version: 2025_05
"""

from typing import NotRequired, TypedDict

"""Public symbols exported by this module."""
__all__ = (
    "OpenCodeAssistantMetadataV2025_05",
    "OpenCodeContentPartV2025_05",
    "OpenCodeMessageDataV2025_05",
    "OpenCodeMessageMetadataV2025_05",
    "OpenCodeMessageTimeV2025_05",
    "OpenCodeSessionDataV2025_05",
    "OpenCodeSessionStateV2025_05",
    "OpenCodeTimeV2025_05",
)


class OpenCodeTimeV2025_05(TypedDict):
    """Time metadata attached to a session."""

    created: NotRequired[int | float]
    updated: NotRequired[int | float]


class OpenCodeSessionDataV2025_05(TypedDict):
    """Parsed payload of a single OpenCode session JSON file."""

    title: NotRequired[str | None]
    slug: NotRequired[str]
    version: NotRequired[str]
    time: NotRequired[OpenCodeTimeV2025_05]


class OpenCodeAssistantMetadataV2025_05(TypedDict):
    """Assistant-specific metadata on a message."""

    modelID: NotRequired[str]
    providerID: NotRequired[str]


class OpenCodeMessageTimeV2025_05(TypedDict):
    """Time metadata attached to a message."""

    created: NotRequired[int | float]
    completed: NotRequired[int | float]


class OpenCodeMessageMetadataV2025_05(TypedDict):
    """Metadata object inside a message file."""

    sessionID: NotRequired[str]
    time: NotRequired[OpenCodeMessageTimeV2025_05]
    assistant: NotRequired[OpenCodeAssistantMetadataV2025_05]


class OpenCodeContentPartV2025_05(TypedDict):
    """One content part within a message."""

    type: str
    text: NotRequired[str]


class OpenCodeMessageDataV2025_05(TypedDict):
    """Parsed payload of a single OpenCode message JSON file."""

    id: NotRequired[str]
    role: str
    parts: NotRequired[list[OpenCodeContentPartV2025_05]]
    metadata: NotRequired[OpenCodeMessageMetadataV2025_05]


class OpenCodeSessionStateV2025_05(TypedDict):
    """Bundled state object for the bidirectional lens.

    Groups a session file with its associated messages so both halves of the
    lens have access to all data needed to build a ``ChatSessionV1``.
    """

    session_id: str
    source_path: str
    session: OpenCodeSessionDataV2025_05
    messages: list[OpenCodeMessageDataV2025_05]
