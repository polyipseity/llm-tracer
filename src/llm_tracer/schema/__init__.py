"""Canonical chat schema – re-exports the current version's types.

Compatible with the OpenAI Chat Completions API ``messages`` format, with
additional metadata extensions for tracing and incremental ingestion.

Each schema version lives in its own ``v{n}.py`` module. This module always
re-exports the *latest* version's types as ``ChatSession`` and ``Message``.
Current version: 1.
"""

from pydantic import BaseModel, Field

from llm_tracer.schema.v1 import AttachmentPolicy
from llm_tracer.schema.v1 import AttachmentV1 as Attachment
from llm_tracer.schema.v1 import ChatSessionV1 as ChatSession
from llm_tracer.schema.v1 import MessageV1 as Message

"""Current schema format version number."""
CURRENT_VERSION: int = 1


class IngestStats(BaseModel):
    """Statistics from one ingest_source() execution."""

    newly_inserted: int = Field(
        ...,
        ge=0,
        description="Number of sessions with new chat IDs never seen before",
    )
    already_ingested: int = Field(
        ...,
        ge=0,
        description="Sessions with known ingest_key (idempotent duplicates)",
    )
    updated: int = Field(
        ...,
        ge=0,
        description="Sessions merged with existing storage (tags/messages extended)",
    )
    errors: list[dict[str, str]] = Field(
        default_factory=list,
        description="Per-file/session parse failures [{'source': str, 'reason': str}, ...]",
    )


"""Public symbols exported by this module."""
__all__ = (
    "Attachment",
    "AttachmentPolicy",
    "CURRENT_VERSION",
    "ChatSession",
    "Message",
    "IngestStats",
)
