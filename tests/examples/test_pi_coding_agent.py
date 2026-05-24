"""Tests that exercise the PI Coding Agent adapter example script."""

import importlib.util
from pathlib import Path
from types import ModuleType

"""Public symbols exported by this test module (none)."""
__all__ = ()

"""Absolute path to the examples/adapters directory."""
_EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples" / "adapters"


def _load_example(name: str) -> ModuleType:
    """Load an example module by filename stem from ``examples/adapters/``."""
    path = _EXAMPLES_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pi_coding_agent_example() -> None:
    """Run the PI Coding Agent adapter example and verify it passes all assertions."""
    _load_example("pi_coding_agent").main()
