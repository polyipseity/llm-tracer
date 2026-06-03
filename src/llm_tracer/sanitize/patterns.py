"""Regex-based pattern registry for deterministic secret redaction.

Provides built-in patterns for common secret formats (API keys, tokens,
credentials) and allows user-defined custom patterns.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Pattern

"""Public symbols exported by this module."""
__all__ = (
    "PatternRegistry",
    "get_builtin_pattern_descriptions",
    "get_builtin_pattern_names",
)

"""Replacement template format string for pattern matches."""
_REDACTED_PATTERN = "[REDACTED_PATTERN_{}]"


@dataclass(frozen=True)
class _BuiltinPattern:
    """A built-in regex pattern for detecting common secret formats."""

    name: str
    description: str
    regex: Pattern[str]
    enabled_by_default: bool = True


"""Built-in patterns for common secret formats."""
_BUILTIN_PATTERNS: dict[str, _BuiltinPattern] = {
    "github_token": _BuiltinPattern(
        name="github_token",
        description="GitHub personal access tokens (ghp_, gho_, ghu_, ghs_, ghr_)",
        regex=re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[0-9a-zA-Z]{36,40}"),
    ),
    "github_fine_grained": _BuiltinPattern(
        name="github_fine_grained",
        description="GitHub fine-grained access token (github_pat_)",
        regex=re.compile(r"github_pat_[0-9a-zA-Z]{22,}"),
    ),
    "aws_access_key": _BuiltinPattern(
        name="aws_access_key",
        description="AWS access key ID (AKIA... etc.)",
        regex=re.compile(r"AKIA[0-9A-Z]{16}"),
    ),
    "slack_token": _BuiltinPattern(
        name="slack_token",
        description="Slack bot/user token (xoxb-, xoxp-)",
        regex=re.compile(r"xox[baprs]-[0-9a-zA-Z-]{10,}"),
    ),
    "openai_api_key": _BuiltinPattern(
        name="openai_api_key",
        description="OpenAI API key (sk-...)",
        regex=re.compile(r"sk-[A-Za-z0-9]{20,}"),
    ),
    "discord_token": _BuiltinPattern(
        name="discord_token",
        description="Discord bot token",
        regex=re.compile(r"[A-Za-z0-9_]{24}\.[A-Za-z0-9_]{6}\.[A-Za-z0-9_]{27}"),
    ),
    "google_api_key": _BuiltinPattern(
        name="google_api_key",
        description="Google API key (AIza...)",
        regex=re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    ),
    "jwt_token": _BuiltinPattern(
        name="jwt_token",
        description="JWT token (eyJ... base64url-encoded)",
        regex=re.compile(
            r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"
        ),
    ),
    "private_key_header": _BuiltinPattern(
        name="private_key_header",
        description="Private key PEM header (-----BEGIN ... PRIVATE KEY-----)",
        regex=re.compile(r"-----BEGIN\s[A-Z\s]+PRIVATE\s*KEY-----"),
    ),
    "generic_token_param": _BuiltinPattern(
        name="generic_token_param",
        description="Generic token-like parameter in URL/query (api_key=, token=)",
        regex=re.compile(
            r"(?i)(?:api[_-]?key|token|secret|password|passwd|auth)=[^\s&]+"
        ),
        enabled_by_default=False,
    ),
}


def get_builtin_pattern_names() -> tuple[str, ...]:
    """Return the names of all built-in patterns."""
    return tuple(_BUILTIN_PATTERNS.keys())


def get_builtin_pattern_descriptions() -> tuple[tuple[str, str, bool], ...]:
    """Return ``(name, description, enabled_by_default)`` for all built-in patterns."""
    return tuple(
        (p.name, p.description, p.enabled_by_default)
        for p in _BUILTIN_PATTERNS.values()
    )


class PatternRegistry:
    """Registry of regex patterns for deterministic secret redaction.

    Applies configured built-in and custom regex patterns to text,
    replacing matches with ``[REDACTED_PATTERN_<name>]`` markers.
    """

    def __init__(self, config: Mapping[str, bool | str] | None = None) -> None:
        """Initialize with optional *config*.

        *config* is a mapping where:
        - Keys matching built-in pattern names control enable/disable (bool).
        - Other keys are treated as custom pattern names mapping to regex strings (str).
        """

        self._patterns: list[tuple[Pattern[str], str]] = []
        if config is None:
            config = {}
        self._configure(config)

    def _configure(self, config: Mapping[str, bool | str]) -> None:
        """Build the active pattern list from *config*."""

        patterns: list[tuple[Pattern[str], str]] = []

        # Built-in patterns
        for name, builtin in _BUILTIN_PATTERNS.items():
            enabled = config.get(name, builtin.enabled_by_default)
            if not isinstance(enabled, bool) or not enabled:
                continue
            patterns.append((builtin.regex, builtin.name))

        # Custom patterns
        for name, value in config.items():
            if name in _BUILTIN_PATTERNS:
                continue
            if not isinstance(value, str):
                continue
            try:
                compiled = re.compile(value)
            except re.error:
                continue
            patterns.append(
                (compiled, f"custom_{name}" if not name.startswith("custom_") else name)
            )

        self._patterns = patterns

    def scrub(self, text: str) -> str:
        """Apply all active patterns and return redacted text.

        Each match is replaced with ``[REDACTED_PATTERN_<name>]``.
        Patterns are applied in registration order.
        """

        for regex, name in self._patterns:
            replacement = _REDACTED_PATTERN.format(name)
            text = regex.sub(replacement, text)
        return text

    @property
    def active_patterns(self) -> tuple[tuple[str, str], ...]:
        """Return ``(name, regex_pattern)`` for all active patterns."""

        return tuple((name, regex.pattern) for regex, name in self._patterns)
