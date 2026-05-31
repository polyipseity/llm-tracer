"""Compatibility wrapper for the Ollama adapter example test."""

from tests.examples.test_example_loader import run_example

"""Public symbols exported by this test module (none)."""
__all__ = ()


def test_ollama_example() -> None:
    """Run the Ollama adapter example and verify it passes assertions."""
    run_example("ollama")
