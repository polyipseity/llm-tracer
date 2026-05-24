"""Thin re-export of the current unified chat schema.

All callers should prefer importing directly from
``llm_tracer.core.unified`` or ``llm_tracer.core.unified.v1``.
"""

from llm_tracer.core.unified import ChatSession, Message

"""Public symbols exported by this module."""
__all__ = ("ChatSession", "Message")
