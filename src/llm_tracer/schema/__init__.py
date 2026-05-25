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

from llm_tracer.schema.v1 import ChatSessionV1 as ChatSession
from llm_tracer.schema.v1 import MessageV1 as Message

"""Current schema format version number."""
CURRENT_VERSION: int = 1

"""Public symbols exported by this module."""
__all__ = ("CURRENT_VERSION", "ChatSession", "Message")
