"""Compatibility wrapper for the local adapter example test."""

from tests.examples.test_example_loader import run_example

"""Public symbols exported by this test module (none)."""
__all__ = ()


def test_local_example() -> None:
    """Run the local adapter example and verify it passes all assertions."""
    run_example("local")
