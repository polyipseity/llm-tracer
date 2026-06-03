"""Unit tests for `llm_tracer.sanitize` — patterns, scrubber, and CLI integration."""

from datetime import datetime
from pathlib import Path

from llm_tracer.config import SanitizeConfig
from llm_tracer.sanitize import PatternRegistry, sanitize_session
from llm_tracer.sanitize.patterns import (
    _BUILTIN_PATTERNS,
    get_builtin_pattern_descriptions,
    get_builtin_pattern_names,
)
from llm_tracer.sanitize.secrets import SecretStore
from llm_tracer.schema import ChatSession, Message

"""Public symbols exported by this test module (none)."""
__all__ = ()


# ── PatternRegistry unit tests ────────────────────────────────────────────────


class TestBuiltinPatternFunctions:
    """Tests for module-level helper functions."""

    def test_get_builtin_pattern_names(self) -> None:
        """get_builtin_pattern_names returns all expected names."""

        names = get_builtin_pattern_names()
        assert "github_token" in names
        assert "aws_access_key" in names
        assert "generic_token_param" in names
        assert isinstance(names, tuple)

    def test_get_builtin_pattern_descriptions(self) -> None:
        """get_builtin_pattern_descriptions returns correctly structured tuples."""

        descriptions = get_builtin_pattern_descriptions()
        assert isinstance(descriptions, tuple)
        assert len(descriptions) > 0
        for name, description, enabled in descriptions:
            assert isinstance(name, str)
            assert isinstance(description, str)
            assert isinstance(enabled, bool)
        names_from_desc = {d[0] for d in descriptions}
        assert names_from_desc == set(_BUILTIN_PATTERNS.keys())


class TestPatternRegistryConfig:
    """Tests for PatternRegistry configuration."""

    def test_default_enables_by_default(self) -> None:
        """Default PatternRegistry (no config) enables only patterns where
        enabled_by_default is True."""

        registry = PatternRegistry()
        active = registry.active_patterns
        active_names = {a[0] for a in active}
        for name, builtin in _BUILTIN_PATTERNS.items():
            if builtin.enabled_by_default:
                assert name in active_names, f"{name} should be active by default"
            else:
                assert name not in active_names, f"{name} should be inactive by default"

    def test_disable_builtin(self) -> None:
        """Disabling a built-in pattern removes it from active set."""

        registry = PatternRegistry({"github_token": False})
        active_names = {a[0] for a in registry.active_patterns}
        assert "github_token" not in active_names

    def test_enable_disabled_by_default(self) -> None:
        """Enabling a disabled-by-default pattern activates it."""

        registry = PatternRegistry({"generic_token_param": True})
        active_names = {a[0] for a in registry.active_patterns}
        assert "generic_token_param" in active_names

    def test_custom_pattern(self) -> None:
        """Custom regex patterns are registered in active set."""

        registry = PatternRegistry({"my_secret": r"SECRET-[A-Z]+"})
        active = dict(registry.active_patterns)
        custom_name = "custom_my_secret"
        assert custom_name in active
        assert active[custom_name] == "SECRET-[A-Z]+"

    def test_custom_pattern_name_starts_with_custom(self) -> None:
        """Custom patterns named 'custom_...' keep their name unchanged."""

        registry = PatternRegistry({"custom_foo": r"FOO-\d+"})
        active = dict(registry.active_patterns)
        assert "custom_foo" in active

    def test_invalid_regex_custom_pattern(self) -> None:
        """Invalid regex in custom pattern is silently skipped."""

        registry = PatternRegistry({"bad": r"[invalid"})
        active_names = {a[0] for a in registry.active_patterns}
        assert "custom_bad" not in active_names

    def test_none_config(self) -> None:
        """Passing None config is equivalent to empty dict."""

        registry = PatternRegistry()
        registry_none = PatternRegistry(None)
        assert registry.active_patterns == registry_none.active_patterns


class TestPatternRegistryScrub:
    """Tests for PatternRegistry.scrub()."""

    GITHUB_TOKEN = "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789"

    def test_scrub_github_token(self) -> None:
        """Built-in github_token pattern redacts GitHub PATs."""

        registry = PatternRegistry()
        result = registry.scrub(f"token is {self.GITHUB_TOKEN} here")
        assert "[REDACTED_PATTERN_github_token]" in result
        assert self.GITHUB_TOKEN not in result

    def test_scrub_multiple_matches(self) -> None:
        """Multiple matches of same pattern are all redacted."""

        registry = PatternRegistry()
        text = f"first {self.GITHUB_TOKEN} second {self.GITHUB_TOKEN}"
        result = registry.scrub(text)
        assert result.count("[REDACTED_PATTERN_github_token]") == 2

    def test_scrub_no_match(self) -> None:
        """Text with no matching patterns is unchanged."""

        registry = PatternRegistry()
        text = "hello world, nothing secret here"
        assert registry.scrub(text) == text

    def test_scrub_custom_pattern(self) -> None:
        """Custom pattern redacts matching text."""

        registry = PatternRegistry({"custom_api": r"API-KEY-\d{4}"})
        result = registry.scrub("my API-KEY-1234 is secret")
        assert "[REDACTED_PATTERN_custom_api]" in result
        assert "API-KEY-1234" not in result

    def test_scrub_multiple_patterns(self) -> None:
        """Multiple active patterns all apply."""

        registry = PatternRegistry({"github_token": True, "aws_access_key": True})
        token = "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789"
        text = f"{token} and AKIA1234567890123456"
        result = registry.scrub(text)
        assert "[REDACTED_PATTERN_github_token]" in result
        assert "[REDACTED_PATTERN_aws_access_key]" in result

    def test_scrub_disabled_pattern_skipped(self) -> None:
        """Disabled built-in pattern does not redact."""

        token = "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789"
        registry = PatternRegistry({"github_token": False})
        result = registry.scrub(f"token is {token}")
        assert token in result
        assert "[REDACTED_PATTERN_github_token]" not in result


class TestScrubberWithPatterns:
    """Integration: _Scrubber with patterns through sanitize_session()."""

    def test_sanitize_session_applies_patterns(self, tmp_path: Path) -> None:
        """sanitize_session() with pattern_registry redacts pattern matches."""

        store = SecretStore(tmp_path / "secrets")
        registry = PatternRegistry({"github_token": True})
        scrubber = __import__("llm_tracer.sanitize", fromlist=["_Scrubber"])._Scrubber(
            secret_store=store, pattern_registry=registry
        )
        session = ChatSession(
            id="test-001",
            source="test",
            timestamp=datetime(2025, 1, 1),
            model="test-model",
            source_record_id="rec-001",
            messages=[
                Message(
                    role="user",
                    content="my token is ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789",
                )
            ],
        )
        sanitized = sanitize_session(session, scrubber, phase_b=False)
        text = sanitized.messages[0].content
        assert "[REDACTED_PATTERN_github_token]" in text
        assert "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789" not in text

    def test_sanitize_session_no_patterns_noop(self, tmp_path: Path) -> None:
        """sanitize_session() without pattern_registry does not apply Phase C."""

        store = SecretStore(tmp_path / "secrets")
        scrubber = __import__("llm_tracer.sanitize", fromlist=["_Scrubber"])._Scrubber(
            secret_store=store, pattern_registry=None
        )
        token = "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789"
        session = ChatSession(
            id="test-002",
            source="test",
            timestamp=datetime(2025, 1, 1),
            model="test-model",
            source_record_id="rec-002",
            messages=[Message(role="user", content=f"token is {token}")],
        )
        sanitized = sanitize_session(session, scrubber, phase_b=False)
        # Without pattern_registry, Phase C does nothing
        assert token in sanitized.messages[0].content

    def test_phase_c_flag(self, tmp_path: Path) -> None:
        """phase_c=False prevents pattern redaction even with registry set."""

        store = SecretStore(tmp_path / "secrets")
        registry = PatternRegistry({"github_token": True})
        scrubber = __import__("llm_tracer.sanitize", fromlist=["_Scrubber"])._Scrubber(
            secret_store=store, pattern_registry=registry
        )
        token = "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789"
        session = ChatSession(
            id="test-003",
            source="test",
            timestamp=datetime(2025, 1, 1),
            model="test-model",
            source_record_id="rec-003",
            messages=[Message(role="user", content=f"token is {token}")],
        )
        sanitized = sanitize_session(session, scrubber, phase_b=False, phase_c=False)
        assert token in sanitized.messages[0].content
        assert "[REDACTED_PATTERN_github_token]" not in sanitized.messages[0].content


class TestSanitizeConfig:
    """Tests for SanitizeConfig.to_pattern_config()."""

    def test_to_pattern_config_empty(self) -> None:
        """Empty SanitizeConfig produces empty dict."""

        cfg = SanitizeConfig()
        assert cfg.to_pattern_config() == {}

    def test_to_pattern_config_merge(self) -> None:
        """to_pattern_config merges patterns and custom_patterns."""

        cfg = SanitizeConfig(
            patterns={"github_token": False},
            custom_patterns={"my_regex": r"FOO-\d+"},
        )
        merged = cfg.to_pattern_config()
        assert merged["github_token"] is False
        assert merged["my_regex"] == r"FOO-\d+"

    def test_custom_overrides_builtin_flag(self) -> None:
        """Custom pattern with same name as builtin flag is overridden (str wins)."""

        cfg = SanitizeConfig(
            patterns={"dup": True},
            custom_patterns={"dup": r"regex"},
        )
        merged = cfg.to_pattern_config()
        # custom_patterns update overwrites: str value wins
        assert merged["dup"] == r"regex"


class TestCliPatternsCommand:
    """Smoke test for ``llm-tracer secrets patterns`` CLI output."""

    def test_get_builtin_pattern_descriptions_includes_all(self) -> None:
        """All _BUILTIN_PATTERNS entries have matching descriptions."""

        descriptions = dict((d[0], d) for d in get_builtin_pattern_descriptions())
        for name in _BUILTIN_PATTERNS:
            assert name in descriptions
            _, desc, enabled = descriptions[name]
            assert desc
            assert isinstance(enabled, bool)
