"""VS Code Copilot Chat upstream format – current version: 1.

For migrations between upstream format versions, each adjacent pair has a
bidirectional ``Iso`` lens in ``v{n}_to_v{n+1}.py``::

    from lenses import bind
    v2_state = bind(v1_state).Iso(v1_to_v2_func, v2_to_v1_func).get()

Current version: 1
"""

from llm_tracer.adapters.vscode.upstream.v1 import (
    VSCodeMessagePayloadV1 as VSCodeMessagePayload,
)
from llm_tracer.adapters.vscode.upstream.v1 import (
    VSCodeRequestV1 as VSCodeRequest,
)
from llm_tracer.adapters.vscode.upstream.v1 import (
    VSCodeResponsePartV1 as VSCodeResponsePart,
)
from llm_tracer.adapters.vscode.upstream.v1 import (
    VSCodeSessionStateV1 as VSCodeSessionState,
)

"""Current upstream format version number."""
CURRENT_VERSION: int = 1

"""Public symbols exported by this module."""
__all__ = (
    "CURRENT_VERSION",
    "VSCodeMessagePayload",
    "VSCodeRequest",
    "VSCodeResponsePart",
    "VSCodeSessionState",
)
