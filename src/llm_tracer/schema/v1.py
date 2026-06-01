"""Unified chat session schema – version 1.

The messages array is compatible with the OpenAI Chat Completions API
message format (https://platform.openai.com/docs/api-reference/chat/create).
Additional fields (id, source, tags, etc.) are metadata extensions.

Future versions will be defined in v2.py, v3.py, …  Each ``v{n+1}.py``
includes the bidirectional Isomorphism lens from the previous version,
enabling lossless round-trip migration across the full version chain.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

"""Public symbols exported by this module."""
__all__ = (
    "AttachmentPolicy",
    "AttachmentV1",
    "ChatSessionV1",
    "MessageV1",
)


class AttachmentPolicy(str, Enum):
    """Policy for handling attachments in chat sessions."""

    STRIP = "strip"
    METADATA_ONLY = "metadata_only"
    FULL = "full"


class AttachmentV1(BaseModel):
    """Attachment metadata and optional content.

    The content field is populated based on the session's attachment_policy:
    - STRIP: attachment not present
    - METADATA_ONLY: content is None
    - FULL: content contains the full attachment data
    """

    name: str = Field(..., description="Filename")
    mime_type: str = Field(..., description="MIME type")
    content: str | None = Field(
        default=None,
        description="Attachment data (if FULL policy)",
    )


class MessageV1(BaseModel):
    """One message in a chat session (OpenAI Chat Completions compatible).

    Compatible with the OpenAI Chat Completions API messages array format.
    The native_id field is a metadata extension for per-message identity.
    """

    role: str = Field(..., description="System, user, assistant, or tool")
    content: str = Field(..., description="Message text")
    tool_calls: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional tool call payloads",
    )
    native_id: str | None = Field(
        default=None,
        description="Source-native message identifier",
    )
    attachments: list[AttachmentV1] = Field(
        default_factory=list,
        description="Message attachments",
    )
    timestamp: datetime | None = Field(
        default=None,
        description="ISO 8601 UTC message timestamp, if available",
    )
    model: str | None = Field(
        default=None,
        description="Per-message model identifier, if available",
    )


class ChatSessionV1(BaseModel):
    """A versioned normalized chat session record – version 1.

    The messages field follows the OpenAI Chat Completions API message format.
    The remaining fields are metadata extensions for tracing, tagging, and
    incremental ingestion.
    """

    id: str = Field(
        ...,
        description="Stable identity key derived from (source, source_record_id)",
    )
    source: str = Field(
        ...,
        description="Source slug: vscode, lmstudio, pi_coding_agent, etc.",
    )
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 UTC execution timestamp",
    )
    model: str = Field(..., description="Model identifier")
    messages: list[MessageV1]
    tags: list[str] = Field(
        default_factory=list,
        description="Hierarchical tags separated by '/'",
    )
    source_record_id: str = Field(
        ...,
        description="Source-native stable identifier",
    )
    ingest_key: str | None = Field(
        default=None,
        description="Ingestion lineage key",
    )
    attachment_policy: AttachmentPolicy = Field(
        default=AttachmentPolicy.METADATA_ONLY,
        description="Attachment handling policy",
    )
