"""VS Code Copilot Chat upstream format – current version: 3.

For migrations between format versions, each ``v{n+1}.py`` defines the
bidirectional ``Iso`` migration lens from v{n} to v{n+1}.

Current version: 3
"""

from llm_tracer.adapters.vscode.raw.v3 import (
    VSCodeMessagePayloadV3 as VSCodeMessagePayload,
)
from llm_tracer.adapters.vscode.raw.v3 import (
    VSCodeRequestV3 as VSCodeRequest,
)
from llm_tracer.adapters.vscode.raw.v3 import (
    VSCodeResponsePartV3 as VSCodeResponsePart,
)
from llm_tracer.adapters.vscode.raw.v3 import (
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
