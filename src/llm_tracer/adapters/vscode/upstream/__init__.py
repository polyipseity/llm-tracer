"""VS Code Copilot Chat upstream format – current version: 3.

For migrations between upstream format versions, each adjacent pair has a
bidirectional ``Iso`` lens in ``v{n}_to_v{n+1}.py``::

    from lenses import bind
    v4_state = bind(v3_state).Iso(v3_to_v4_func, v4_to_v3_func).get()

Current version: 3
"""

from llm_tracer.adapters.vscode.upstream.v3 import (
    VSCodeMessagePayloadV3 as VSCodeMessagePayload,
)
from llm_tracer.adapters.vscode.upstream.v3 import (
    VSCodeRequestV3 as VSCodeRequest,
)
from llm_tracer.adapters.vscode.upstream.v3 import (
    VSCodeResponsePartV3 as VSCodeResponsePart,
)
from llm_tracer.adapters.vscode.upstream.v3 import (
    VSCodeSessionStateV3 as VSCodeSessionState,
)

"The current known VS Code Copilot Chat upstream format version."
CURRENT_VERSION: int = 3

"""Public symbols exported by this module."""
__all__ = (
    "CURRENT_VERSION",
    "VSCodeMessagePayload",
    "VSCodeRequest",
    "VSCodeResponsePart",
    "VSCodeSessionState",
)
