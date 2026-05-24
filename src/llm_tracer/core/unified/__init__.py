"""Unified chat format – current version: 1.

The unified format is designed to be compatible with the OpenAI Chat
Completions API message structure for the ``messages`` field, with
additional metadata extensions for tracing and incremental ingestion.

Versioning convention
---------------------
- Each schema version lives in its own ``v{n}.py`` module.
- Each adjacent pair of versions has a bidirectional lossless
  ``Isomorphism`` lens in ``v{n}_to_v{n+1}.py``, created with::

      from lenses.optics import Isomorphism
      v1_to_v2 = Isomorphism(fwd_func, bwd_func)

  This enables lossless round-trip migration across the full version chain.
- This module always re-exports the *latest* version's types as
  ``ChatSession`` and ``Message``.

Current version: 1
"""

from llm_tracer.core.unified.v1 import ChatSessionV1 as ChatSession
from llm_tracer.core.unified.v1 import MessageV1 as Message

"""Current unified format version number."""
CURRENT_VERSION: int = 1

"""Public symbols exported by this module."""
__all__ = ("CURRENT_VERSION", "ChatSession", "Message")
