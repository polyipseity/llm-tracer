"""Unified chat session schema – version 1.

The messages array is compatible with the OpenAI Chat Completions API
message format (https://platform.openai.com/docs/api-reference/chat/create).
Additional fields (id, source, tags, etc.) are metadata extensions.

Future versions will be defined in v2.py, v3.py, … Each adjacent pair of
versions has a bidirectional Isomorphism lens in a matching
``v{n}_to_v{n+1}.py`` file, enabling lossless round-trip migration across the
full version chain.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

"""Public symbols exported by this module."""
__all__ = ("ChatSessionV1", "MessageV1")


class MessageV1(BaseModel):
    """One message in a chat session (OpenAI Chat Completions compatible).

    Compatible with the OpenAI Chat Completions API messages array format.
    The native_id field is a metadata extension for per-message identity.
    """

    role: str = Field(..., description="System, user, assistant, or tool")
    content: str = Field(..., description="Raw markdown message payload string")
    tool_calls: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional normalized tool call payloads.",
    )
    native_id: str | None = Field(
        default=None,
        description="Source-native message identifier for per-message identity and incremental deduplication.",
    )


class ChatSessionV1(BaseModel):
    """A versioned normalized chat session record – version 1.

    The messages field follows the OpenAI Chat Completions API message format.
    The remaining fields are metadata extensions for tracing, tagging, and
    incremental ingestion.
    """

    id: str = Field(
        ...,
        description="Stable BLAKE3 identity key derived from (source, source_record_id), invariant under message additions.",
    )
    source: str = Field(
        ...,
        description="Source slug: vscode, lmstudio, pi_coding_agent, etc.",
    )
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 UTC execution timestamp with timezone info",
    )
    model: str = Field(..., description="Target model identifier string")
    messages: list[MessageV1]
    tags: list[str] = Field(
        default_factory=list,
        description="Hierarchical tags separated by '/'.",
    )
    source_record_id: str | None = Field(
        default=None,
        description="Optional stable source-native identifier.",
    )
    ingest_key: str | None = Field(
        default=None,
        description="Deterministic ingestion lineage key.",
    )
