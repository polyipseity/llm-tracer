"""Compatibility wrapper for the OpenCode adapter example test."""

from tests.examples.test_example_loader import run_example

"""Public symbols exported by this test module (none)."""
__all__ = ()


def test_opencode_example() -> None:
    """Run the OpenCode adapter example and verify it passes all assertions."""
    run_example("opencode")
