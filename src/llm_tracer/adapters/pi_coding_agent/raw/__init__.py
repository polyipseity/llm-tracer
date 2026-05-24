"""PI Coding Agent trace upstream format – current version: 2025_01.

The 2025-01 format is date-based (undocumented, reverse-engineered format).
For migrations between upstream format versions, each adjacent pair has a
bidirectional ``Iso`` lens in ``v{prev}_to_v{next}.py``::

    from lenses import bind
    v2025_02_trace = bind(v2025_01_trace).Iso(
        v2025_01_to_v2025_02_func, v2025_02_to_v2025_01_func
    ).get()

Current version: 2025_01
"""

from llm_tracer.adapters.pi_coding_agent.raw.v2025_01 import (
    PiCodingAgentStepV2025_01 as PiCodingAgentStep,
)
from llm_tracer.adapters.pi_coding_agent.raw.v2025_01 import (
    PiCodingAgentTraceV2025_01 as PiCodingAgentTrace,
)

"The current known PI Coding Agent upstream format version identifier."
CURRENT_VERSION: str = "2025_01"

"""Public symbols exported by this module."""
__all__ = (
    "CURRENT_VERSION",
    "PiCodingAgentStep",
    "PiCodingAgentTrace",
)
