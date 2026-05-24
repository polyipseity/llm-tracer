---
description: "Use when editing Python modules in src, tests, scripts, or .agents/skills. Enforces __all__ tuple rules, docstring coverage, strict typing, and uv-locked quality commands."
name: "Python Quality Gates"
applyTo: "src/**/*.py, tests/**/*.py, scripts/**/*.py, .agents/skills/**/*.py"
---

# Python Quality Gates

- Keep a non-empty module docstring in every Python module.
- Define module-level `__all__` as a tuple of string literals.
- Keep `__all__` after top-level imports.
- Add docstrings for:
  - all top-level functions, async functions, and classes
  - nested functions and methods
  - top-level assignments/constants via an immediately preceding
    string-literal expression
- Use complete type annotations compatible with Ty strict mode
  (`python-version = "3.14"`).
- Prefer top-level imports; avoid import-outside-top-level patterns unless
  there is a strong reason (`PLC0415` is enabled in Ruff).
- When validating or fixing Python quality, prefer:
  - `uv run --locked ruff check`
  - `uv run --locked ruff format`
  - `uv run --locked pytest`
- When adding or renaming exported symbols, update `__all__` in the same
  change.

## Adapter and Schema Versioning

- Raw adapter TypedDicts (mirroring source JSON) live in `adapters/{name}/raw/v*.py`.
- Canonical schema Pydantic models live in `core/schema/v*.py`.
- Format version identifiers are date-based strings (e.g., `"2025_05"`), except
  when the upstream data carries an explicit version field (e.g., VS Code uses `V3`).
- Migration lenses from v{n} to v{n+1} live **inside** `v{n+1}.py`, not in a
  separate `v{n}_to_v{n+1}.py` file.

See `tests/test_module_exports.py` and `tests/test_docstrings.py` for the
canonical policy checks.
