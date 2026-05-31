"""Helpers for loading and running adapter example modules in tests."""

import importlib.util
from pathlib import Path
from types import ModuleType

"""Public symbols exported by this helper module."""
__all__ = ("run_example",)


"""Absolute path to the ``examples/adapters`` directory."""
_EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples" / "adapters"


def _load_example_module(name: str) -> ModuleType:
    """Load an adapter example module by filename stem."""
    path = _EXAMPLES_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_example(name: str) -> None:
    """Execute ``main()`` for the named adapter example module."""
    _load_example_module(name).main()
