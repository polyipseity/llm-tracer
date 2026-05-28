---
description: "Use when creating or updating tests in tests/** or .agents/skills/**. Covers pytest, anyio async test patterns, deterministic assertions, and repository test command expectations."
name: "Testing with Pytest and AnyIO"
applyTo: "tests/**/*.py, .agents/skills/**/tests_*.py"
---

# Testing with Pytest and AnyIO

- Use `pytest` conventions and keep tests deterministic.
- Prefer `@pytest.mark.anyio` for async tests.
- Keep async backend expectations aligned with `tests/conftest.py`
  (`("asyncio", {"use_uvloop": True})`).
- Avoid network calls, external side effects, and flaky timing assumptions.
- Prefer explicit, descriptive assertions and failure messages.
- For static-policy checks (exports/docstrings), prefer AST parsing over
  importing modules with side effects.
- Keep tests in the configured paths:
  - `tests/`
  - `.agents/skills/**/tests_*`

Run test validation with `uv run --locked pytest`.

## Ingest/Purge Requirements for Adapters

- For every adapter source, include tests proving `ingest_source` is idempotent:
  first run inserts records, second run returns `0`.
- For every adapter source, include tests proving `purge_ingested_source` works:
  first purge removes ingested records, second purge returns `0`.
- Include at least one test ensuring manually authored chats (`ingest_key = None`)
  are preserved by `purge_ingested_source`.
- Prefer shared parametrized tests over per-adapter duplication when behavior is
  consistent across adapters.
