"""Compatibility wrapper for the Claude Code adapter example test."""

from tests.examples.test_example_loader import run_example

"""Public symbols exported by this test module (none)."""
__all__ = ()


def test_claude_code_example() -> None:
    """Run the Claude Code adapter example and verify it passes assertions."""
    run_example("claude_code")
