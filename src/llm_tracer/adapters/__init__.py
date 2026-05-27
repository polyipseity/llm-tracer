"""Adapter registry for source-specific ingestion pipelines."""

from llm_tracer.adapters.base import BaseAdapter
from llm_tracer.adapters.claude_code import ClaudeCodeAdapter
from llm_tracer.adapters.codex import CodexAdapter
from llm_tracer.adapters.lmstudio import LMStudioAdapter
from llm_tracer.adapters.local import LocalAdapter
from llm_tracer.adapters.ollama import OllamaAdapter
from llm_tracer.adapters.opencode import OpenCodeAdapter
from llm_tracer.adapters.oterm import OTermAdapter
from llm_tracer.adapters.pi_coding_agent import PiCodingAgentAdapter
from llm_tracer.adapters.vscode import VSCodeAdapter

"""Public symbols exported by this module."""
__all__ = ("ADAPTERS", "BaseAdapter", "get_adapter")


"""Registry mapping source slugs to adapter classes."""
_ADAPTERS = {
    "claude_code": ClaudeCodeAdapter,
    "codex": CodexAdapter,
    "local": LocalAdapter,
    "lmstudio": LMStudioAdapter,
    "ollama": OllamaAdapter,
    "opencode": OpenCodeAdapter,
    "oterm": OTermAdapter,
    "pi_coding_agent": PiCodingAgentAdapter,
    "vscode": VSCodeAdapter,
}


"""Public immutable adapter name list."""
ADAPTERS = tuple(sorted(_ADAPTERS))


def get_adapter(source: str) -> BaseAdapter:
    """Build an adapter instance for a configured source slug."""

    try:
        adapter_type = _ADAPTERS[source]
    except KeyError as exc:
        known = ", ".join(ADAPTERS)
        raise ValueError(
            f"unknown source {source!r}; expected one of: {known}"
        ) from exc
    return adapter_type()
