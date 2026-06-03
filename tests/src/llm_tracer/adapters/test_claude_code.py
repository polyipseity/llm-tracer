"""Unit tests for `llm_tracer.adapters.claude_code`."""

from llm_tracer.adapters.claude_code import _extract_workspace_folder

"""Public symbols exported by this test module (none)."""
__all__ = ()


class TestExtractWorkspaceFolder:
    """Tests for ``_extract_workspace_folder`` encoding decoder."""

    def test_encoded_full_path(self) -> None:
        """Decode full encoded path — extracts last dash-separated segment.

        Note: project names containing ``-`` are lossy (the dash is
        indistinguishable from a path separator in Claude Code's encoding).
        """
        result = _extract_workspace_folder(
            "-Users-polyipseity-dev-monorepo-self-llm-tracer"
        )
        assert result == "tracer"

    def test_encoded_path_with_hidden_dir(self) -> None:
        """Handle double dash from hidden dir like ``~/.bun/bin``."""
        result = _extract_workspace_folder("-Users-polyipseity--bun-bin")
        assert result == "bin"

    def test_plain_name_passes_through(self) -> None:
        """Non-encoded directory names should pass unchanged."""
        result = _extract_workspace_folder("example-project")
        assert result == "example-project"

    def test_single_component_after_strip(self) -> None:
        """Encoded path with only one component after stripping leading dash."""
        result = _extract_workspace_folder("-myproject")
        assert result == "myproject"

    def test_empty_string(self) -> None:
        """Empty string should return empty string."""
        result = _extract_workspace_folder("")
        assert result == ""

    def test_only_dash(self) -> None:
        """Lone dash returns empty string."""
        result = _extract_workspace_folder("-")
        assert result == ""
