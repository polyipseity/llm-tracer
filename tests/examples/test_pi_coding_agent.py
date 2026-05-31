"""Compatibility wrapper for the PI Coding Agent adapter example test."""

from tests.examples.test_example_loader import run_example

"""Public symbols exported by this test module (none)."""
__all__ = ()


def test_pi_coding_agent_example() -> None:
    """Run the PI Coding Agent adapter example and verify it passes all assertions."""
    run_example("pi_coding_agent")
