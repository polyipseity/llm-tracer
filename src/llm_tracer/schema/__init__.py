"""Canonical chat schema – current version: 1.

The schema format is designed to be compatible with the OpenAI Chat
Completions API message structure for the ``messages`` field, with
additional metadata extensions for tracing and incremental ingestion.

Versioning convention
---------------------
- Each schema version lives in its own ``v{n}.py`` module.
- Each ``v{n+1}.py`` defines the bidirectional lossless ``Iso`` migration lens
  from v{n} to v{n+1}, created with::

      from lenses import bind

      # Forward: convert a v1 session to v2
      v2_session = bind(v1_session).Iso(v1_to_v2_func, v2_to_v1_func).get()

      # Backward: recover v1 from v2
      v1_session = bind(v1_session).Iso(v1_to_v2_func, v2_to_v1_func).set(v2_session)

  The ``.set()`` call applies the backward function to the argument.

- This module always re-exports the *latest* version's types as
  ``ChatSession`` and ``Message``.

Current version: 1
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
