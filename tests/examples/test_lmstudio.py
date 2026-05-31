"""Compatibility wrapper for the LM Studio adapter example test."""

from tests.examples.test_example_loader import run_example

"""Public symbols exported by this test module (none)."""
__all__ = ()


def test_lmstudio_example() -> None:
    """Run the LM Studio adapter example and verify it passes all assertions."""
    run_example("lmstudio")
