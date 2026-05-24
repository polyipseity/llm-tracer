"""OpenCode JSON upstream format – current version: 2025_01.

The 2025-01 format is date-based.  The ``version`` field in OpenCode JSON is
the application semver string, not a schema version discriminator.
For migrations between upstream format versions, each adjacent pair has a
bidirectional ``Iso`` lens in ``v{prev}_to_v{next}.py``::

    from lenses import bind
    v2025_02_state = bind(v2025_01_state).Iso(
        v2025_01_to_v2025_02_func, v2025_02_to_v2025_01_func
    ).get()

Current version: 2025_01
"""

from llm_tracer.adapters.opencode.upstream.v2025_01 import (
    OpenCodeAssistantMetadataV2025_01 as OpenCodeAssistantMetadata,
)
from llm_tracer.adapters.opencode.upstream.v2025_01 import (
    OpenCodeContentPartV2025_01 as OpenCodeContentPart,
)
from llm_tracer.adapters.opencode.upstream.v2025_01 import (
    OpenCodeMessageDataV2025_01 as OpenCodeMessageData,
)
from llm_tracer.adapters.opencode.upstream.v2025_01 import (
    OpenCodeMessageMetadataV2025_01 as OpenCodeMessageMetadata,
)
from llm_tracer.adapters.opencode.upstream.v2025_01 import (
    OpenCodeMessageTimeV2025_01 as OpenCodeMessageTime,
)
from llm_tracer.adapters.opencode.upstream.v2025_01 import (
    OpenCodeSessionDataV2025_01 as OpenCodeSessionData,
)
from llm_tracer.adapters.opencode.upstream.v2025_01 import (
    OpenCodeSessionStateV2025_01 as OpenCodeSessionState,
)
from llm_tracer.adapters.opencode.upstream.v2025_01 import (
    OpenCodeTimeV2025_01 as OpenCodeTime,
)

"The current known OpenCode upstream format version identifier."
CURRENT_VERSION: str = "2025_01"

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
