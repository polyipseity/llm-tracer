"""OpenCode JSON upstream format – current version: 1.

For migrations between upstream format versions, each adjacent pair has a
bidirectional ``Iso`` lens in ``v{n}_to_v{n+1}.py``::

    from lenses import bind
    v2_state = bind(v1_state).Iso(v1_to_v2_func, v2_to_v1_func).get()

Current version: 1
"""

from llm_tracer.adapters.opencode.upstream.v1 import (
    OpenCodeAssistantMetadataV1 as OpenCodeAssistantMetadata,
)
from llm_tracer.adapters.opencode.upstream.v1 import (
    OpenCodeContentPartV1 as OpenCodeContentPart,
)
from llm_tracer.adapters.opencode.upstream.v1 import (
    OpenCodeMessageDataV1 as OpenCodeMessageData,
)
from llm_tracer.adapters.opencode.upstream.v1 import (
    OpenCodeMessageMetadataV1 as OpenCodeMessageMetadata,
)
from llm_tracer.adapters.opencode.upstream.v1 import (
    OpenCodeMessageTimeV1 as OpenCodeMessageTime,
)
from llm_tracer.adapters.opencode.upstream.v1 import (
    OpenCodeSessionDataV1 as OpenCodeSessionData,
)
from llm_tracer.adapters.opencode.upstream.v1 import (
    OpenCodeSessionStateV1 as OpenCodeSessionState,
)
from llm_tracer.adapters.opencode.upstream.v1 import (
    OpenCodeTimeV1 as OpenCodeTime,
)

"""Current upstream format version number."""
CURRENT_VERSION: int = 1

"""Public symbols exported by this module."""
__all__ = (
    "CURRENT_VERSION",
    "OpenCodeAssistantMetadata",
    "OpenCodeContentPart",
    "OpenCodeMessageData",
    "OpenCodeMessageMetadata",
    "OpenCodeMessageTime",
    "OpenCodeSessionData",
    "OpenCodeSessionState",
    "OpenCodeTime",
)
