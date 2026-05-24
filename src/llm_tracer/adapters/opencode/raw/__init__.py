"""OpenCode JSON upstream format – current version: 2025_05.

The 2025-05 format is date-based.  The ``version`` field in OpenCode JSON is
the application semver string, not a schema version discriminator.
OpenCode's first public release was v0.0.45 on 2025-05-15; this JSON format
was in use until the SQLite migration in approximately February 2026.

Current version: 2025_05
"""

from llm_tracer.adapters.opencode.raw.v2025_05 import (
    OpenCodeAssistantMetadataV2025_05 as OpenCodeAssistantMetadata,
)
from llm_tracer.adapters.opencode.raw.v2025_05 import (
    OpenCodeContentPartV2025_05 as OpenCodeContentPart,
)
from llm_tracer.adapters.opencode.raw.v2025_05 import (
    OpenCodeMessageDataV2025_05 as OpenCodeMessageData,
)
from llm_tracer.adapters.opencode.raw.v2025_05 import (
    OpenCodeMessageMetadataV2025_05 as OpenCodeMessageMetadata,
)
from llm_tracer.adapters.opencode.raw.v2025_05 import (
    OpenCodeMessageTimeV2025_05 as OpenCodeMessageTime,
)
from llm_tracer.adapters.opencode.raw.v2025_05 import (
    OpenCodeSessionDataV2025_05 as OpenCodeSessionData,
)
from llm_tracer.adapters.opencode.raw.v2025_05 import (
    OpenCodeSessionStateV2025_05 as OpenCodeSessionState,
)
from llm_tracer.adapters.opencode.raw.v2025_05 import (
    OpenCodeTimeV2025_05 as OpenCodeTime,
)

"The current known OpenCode upstream format version identifier."
CURRENT_VERSION: str = "2025_05"

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
