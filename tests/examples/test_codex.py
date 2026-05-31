"""Compatibility wrapper for the Codex adapter example test."""

from tests.examples.test_example_loader import run_example

"""Public symbols exported by this test module (none)."""
__all__ = ()


def test_codex_example() -> None:
    """Run the Codex adapter example and verify it passes assertions."""
    run_example("codex")
