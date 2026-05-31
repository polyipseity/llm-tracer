---
description: "Use when creating or updating tests in tests/** or .agents/skills/**. Covers pytest, anyio async test patterns, deterministic assertions, and repository test command expectations."
name: "Testing with Pytest and AnyIO"
applyTo: "tests/**/*.py, .agents/skills/**/tests_*.py"
---

# Testing with Pytest and AnyIO

- Use `pytest` conventions and keep tests deterministic.
- Prefer `@pytest.mark.anyio` for async tests (backend configured in `tests/conftest.py`).
- Avoid network calls, external side effects, and flaky timing assumptions.
- Prefer explicit, descriptive assertions and failure messages.
- For policy checks (exports/docstrings), prefer AST parsing over importing.
- Run the canonical locked checks from `AGENTS.md` before finishing.

## Adapter Ingest/Purge Test Requirements

For every adapter, tests must verify:

- **Idempotency:** first `ingest_source()` inserts records, second returns `0`.
- **Purge:** first `purge_ingested_source()` removes ingested records, second returns `0`.
- **Manual-session safety:** purge keeps manually created chats (`ingest_key = None`).

Prefer shared parametrized tests in `tests/src/llm_tracer/test_ingest.py` for consistency
across adapters.
