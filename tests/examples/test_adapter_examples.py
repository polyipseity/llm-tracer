"""Parametrized tests that run every adapter example script and verify its output."""

import pytest

from tests.examples.test_example_loader import run_example

"""Public symbols exported by this test module (none)."""
__all__ = ()

"""All adapter example names, each corresponding to ``examples/adapters/{name}.py``."""
_ADAPTER_NAMES: tuple[str, ...] = (
    "claude_code",
    "codex",
    "lmstudio",
    "local",
    "ollama",
    "opencode",
    "oterm",
    "pi_coding_agent",
    "vscode",
)


@pytest.mark.parametrize("name", _ADAPTER_NAMES)
def test_adapter_example(name: str) -> None:
    """Run the named adapter example and verify it passes all assertions."""
    run_example(name)
