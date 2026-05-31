---
description: "Use when editing Python modules in src, tests, scripts, or .agents/skills. Enforces __all__ tuple rules, docstring coverage, strict typing, and uv-locked quality commands."
name: "Python Quality Gates"
applyTo: "src/**/*.py, tests/**/*.py, scripts/**/*.py, .agents/skills/**/*.py"
---

# Python Quality Gates

See `AGENTS.md` § **Conventions** for core **all** and docstring rules.

Additional specifics:

- Add docstrings for nested functions and methods (not just top-level).
- Use complete type annotations compatible with Ty strict mode
  (`python-version = "3.14"`).
- Prefer top-level imports; `PLC0415` is enabled in Ruff.
- Validate with `uv run --locked ruff check`, `uv run --locked ruff format`,
  `uv run --locked pytest`.

## Adapter and Schema Versioning

- Raw adapter TypedDicts live in `adapters/{name}/raw/v*.py`.
- Canonical schema Pydantic models live in `schema/v*.py`.
- Version identifiers are date-based (`"2025_05"`) or upstream-defined (e.g., VS Code `V3`).
- Migrations from v{n} to v{n+1} live **inside** `v{n+1}.py`.
