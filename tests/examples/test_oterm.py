"""Compatibility wrapper for the oterm adapter example test."""

from tests.examples.test_example_loader import run_example

"""Public symbols exported by this test module (none)."""
__all__ = ()


def test_oterm_example() -> None:
    """Run the oterm adapter example and verify it passes assertions."""
    run_example("oterm")
