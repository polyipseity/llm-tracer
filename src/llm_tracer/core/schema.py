"""Core normalized schema models for chat tracing."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

"""Public symbols exported by this module."""
__all__ = ("ChatSession", "Message")


class Message(BaseModel):
    """A normalized message payload in a conversation."""

    role: str = Field(..., description="System, user, assistant, or tool")
    content: str = Field(..., description="Raw markdown message payload string")
    tool_calls: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional normalized tool call payloads.",
    )


class ChatSession(BaseModel):
    """A normalized chat session record used across ingestion and publishing."""

    id: str = Field(
        ...,
        description="Deterministic SHA256 hash of canonicalized thread content",
    )
    source: str = Field(
        ...,
        description="Source slug: vscode-copilot, lm-studio, pi-agent, etc.",
    )
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 UTC execution timestamp with timezone info",
    )
    model: str = Field(..., description="Target model identifier string")
    messages: list[Message]
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
