"""PI Coding Agent trace upstream format – current version: 1.

For migrations between upstream format versions, each adjacent pair has a
bidirectional ``Iso`` lens in ``v{n}_to_v{n+1}.py``::

    from lenses import bind
    v2_trace = bind(v1_trace).Iso(v1_to_v2_func, v2_to_v1_func).get()

Current version: 1
"""

from llm_tracer.adapters.pi_coding_agent.upstream.v1 import (
    PiCodingAgentStepV1 as PiCodingAgentStep,
)
from llm_tracer.adapters.pi_coding_agent.upstream.v1 import (
    PiCodingAgentTraceV1 as PiCodingAgentTrace,
)

"""Current upstream format version number."""
CURRENT_VERSION: int = 1

"""Public symbols exported by this module."""
__all__ = (
    "CURRENT_VERSION",
    "PiCodingAgentStep",
    "PiCodingAgentTrace",
)
