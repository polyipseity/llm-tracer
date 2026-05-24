"""LM Studio conversation upstream format – current version: 1.

For migrations between upstream format versions, each adjacent pair has a
bidirectional ``Iso`` lens in ``v{n}_to_v{n+1}.py``::

    from lenses import bind
    v2_payload = bind(v1_payload).Iso(v1_to_v2_func, v2_to_v1_func).get()

Current version: 1
"""

from llm_tracer.adapters.lmstudio.upstream.v1 import (
    LMStudioContentPartV1 as LMStudioContentPart,
)
from llm_tracer.adapters.lmstudio.upstream.v1 import (
    LMStudioConversationV1 as LMStudioConversation,
)
from llm_tracer.adapters.lmstudio.upstream.v1 import (
    LMStudioPreprocessedV1 as LMStudioPreprocessed,
)
from llm_tracer.adapters.lmstudio.upstream.v1 import (
    LMStudioTurnV1 as LMStudioTurn,
)
from llm_tracer.adapters.lmstudio.upstream.v1 import (
    LMStudioVersionV1 as LMStudioVersion,
)

"""Current upstream format version number."""
CURRENT_VERSION: int = 1

"""Public symbols exported by this module."""
__all__ = (
    "CURRENT_VERSION",
    "LMStudioContentPart",
    "LMStudioConversation",
    "LMStudioPreprocessed",
    "LMStudioTurn",
    "LMStudioVersion",
)
