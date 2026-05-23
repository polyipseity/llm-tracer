"""Adapter registry for source-specific ingestion pipelines."""

from llm_tracer.adapters.base import BaseAdapter
from llm_tracer.adapters.copilot import CopilotAdapter
from llm_tracer.adapters.lmstudio import LMStudioAdapter
from llm_tracer.adapters.pi_agent import PiAgentAdapter

"""Public symbols exported by this module."""
__all__ = ("ADAPTERS", "BaseAdapter", "get_adapter")


"""Registry mapping source slugs to adapter classes."""
_ADAPTERS = {
    "lmstudio": LMStudioAdapter,
    "copilot": CopilotAdapter,
    "pi_agent": PiAgentAdapter,
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
