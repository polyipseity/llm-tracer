"""LM Studio conversation upstream format – current version: 2024_01.

The 2024-01 format is date-based; there is no explicit version field in the
data.  For migrations between format versions, each ``v{n+1}.py`` defines the
bidirectional ``Iso`` migration lens from v{n} to v{n+1}.

Current version: 2024_01
"""

from llm_tracer.adapters.lmstudio.raw.v2024_01 import (
    LMStudioContentPartV2024_01 as LMStudioContentPart,
)
from llm_tracer.adapters.lmstudio.raw.v2024_01 import (
    LMStudioConversationV2024_01 as LMStudioConversation,
)
from llm_tracer.adapters.lmstudio.raw.v2024_01 import (
    LMStudioPreprocessedV2024_01 as LMStudioPreprocessed,
)
from llm_tracer.adapters.lmstudio.raw.v2024_01 import (
    LMStudioTurnV2024_01 as LMStudioTurn,
)
from llm_tracer.adapters.lmstudio.raw.v2024_01 import (
    LMStudioVersionV2024_01 as LMStudioVersion,
)

"The current known LM Studio upstream format version identifier."
CURRENT_VERSION: str = "2024_01"

"""Public symbols exported by this module."""
__all__ = (
    "CURRENT_VERSION",
    "LMStudioContentPart",
    "LMStudioConversation",
    "LMStudioPreprocessed",
    "LMStudioTurn",
    "LMStudioVersion",
)
