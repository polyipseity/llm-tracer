"""PI Coding Agent trace upstream format types – 2025-01 format.

Note: Storage paths and trace format are speculative — no public documentation
was found for PI Coding Agent's data storage format.  The TypedDicts below
were inferred by reverse-engineering locally captured traces.

The 2025-01 format is date-based (undocumented format).  There is no version
field in the data.

Each trace file contains a single JSON object (``PiCodingAgentTraceV2025_01``)
whose ``messages``, ``events``, or ``steps`` field holds a list of step
objects.

Current version: 2025_01
"""

from typing import Any, NotRequired, TypedDict

"""Public symbols exported by this module."""
__all__ = (
    "PiCodingAgentStepV2025_01",
    "PiCodingAgentTraceV2025_01",
)


class PiCodingAgentStepV2025_01(TypedDict):
    """One step, event, or message within a PI Coding Agent trace."""

    id: NotRequired[str]
    step_id: NotRequired[str]
    role: NotRequired[str]
    content: NotRequired[str | list[Any]]


class PiCodingAgentTraceV2025_01(TypedDict):
    """The parsed payload of a single PI Coding Agent trace file."""

    timestamp: NotRequired[str | None]
    started_at: NotRequired[str | None]
    messages: NotRequired[list[PiCodingAgentStepV2025_01]]
    events: NotRequired[list[PiCodingAgentStepV2025_01]]
    steps: NotRequired[list[PiCodingAgentStepV2025_01]]
    model: NotRequired[str | None]
    agent_model: NotRequired[str | None]
    trace_id: NotRequired[str | None]
    id: NotRequired[str | None]
    run_id: NotRequired[str | None]
    title: NotRequired[str | None]
    name: NotRequired[str | None]
    tags: NotRequired[list[Any]]
