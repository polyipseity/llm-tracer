"""Compatibility wrapper for the VS Code adapter example test."""

from tests.examples.test_example_loader import run_example

"""Public symbols exported by this test module (none)."""
__all__ = ()


def test_vscode_example() -> None:
    """Run the VS Code adapter example and verify it passes all assertions."""
    run_example("vscode")
