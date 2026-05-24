"""PI Coding Agent trace upstream format types – version 1.

Note: Storage paths and trace format are speculative — no public documentation
was found for PI Coding Agent's data storage format.  The TypedDicts below
were inferred by reverse-engineering locally captured traces.

Each trace file contains a single JSON object (``PiCodingAgentTraceV1``) whose
``messages``, ``events``, or ``steps`` field holds a list of step objects.

Current version: 1
"""

from typing import Any, NotRequired, TypedDict

"""Public symbols exported by this module."""
__all__ = (
    "PiCodingAgentStepV1",
    "PiCodingAgentTraceV1",
)


class PiCodingAgentStepV1(TypedDict):
    """One step, event, or message within a PI Coding Agent trace."""

    id: NotRequired[str]
    step_id: NotRequired[str]
    role: NotRequired[str]
    content: NotRequired[str | list[Any]]


class PiCodingAgentTraceV1(TypedDict):
    """The parsed payload of a single PI Coding Agent trace file."""

    timestamp: NotRequired[str | None]
    started_at: NotRequired[str | None]
    messages: NotRequired[list[PiCodingAgentStepV1]]
    events: NotRequired[list[PiCodingAgentStepV1]]
    steps: NotRequired[list[PiCodingAgentStepV1]]
    model: NotRequired[str | None]
    agent_model: NotRequired[str | None]
    trace_id: NotRequired[str | None]
    id: NotRequired[str | None]
    run_id: NotRequired[str | None]
    title: NotRequired[str | None]
    name: NotRequired[str | None]
    tags: NotRequired[list[Any]]
