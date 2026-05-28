---
description: "Use when creating or updating adapter example scripts in examples/adapters/. Enforces that every adapter example must include a corresponding expected.json fixture and verify output against it in main()."
name: "Adapter Example Verification Pattern"
applyTo: "examples/adapters/*.py"
---

# Adapter Example Verification Pattern

Every adapter example script must verify its output against a golden `expected.json` file.

## Fixture Structure

Each adapter fixture in `examples/fixtures/<adapter_name>/` must include:

- **Data files** (e.g., JSON, JSONL, SQLite) that the adapter ingests
- **expected.json** at the root: a list of `ChatSession` objects (serialized via `model_dump(mode="json")`) representing the canonical expected output

Example structure:

```text
examples/fixtures/lmstudio/
├── conversations/
│   └── *.json
└── expected.json
```

## Example Script Pattern

Every `examples/adapters/<name>.py` must:

1. **Define fixture paths:**

   ```python
   FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "<name>" / "<subdir>"
   EXPECTED_JSON = FIXTURE_DIR / "expected.json"  # or parent dir for safety
   ```

2. **In main(), after ingesting sessions, add verification:**

   ```python
   import json as _json

   _expected = _json.loads(EXPECTED_JSON.read_text(encoding="utf-8"))
   _actual = [s.model_dump(mode="json") for s in sessions]
   for _d in _actual + _expected:
       _d.pop("ingest_key", None)  # Always: path-specific, never stable
       # Adapt for unstable timestamps (file mtime-based adapters):
       if adapter_uses_mtime:  # e.g., ollama, oterm
           _d.pop("timestamp", None)
   assert _actual == _expected, "session output does not match expected.json"
   ```

## Timestamp Stability

- **Stable adapters** (claude_code, codex, lmstudio, vscode, opencode, pi_coding_agent, local): Skip only `ingest_key` in comparison
- **Unstable (mtime-based) adapters** (ollama, oterm):
  - Set fixture file mtime to epoch 0 using `os.utime(path, (0, 0))` before ingesting
  - Skip both `ingest_key` and `timestamp` in comparison

## Regenerating expected.json

When fixtures change or new adapters are added:

```python
import json
adapter = SomeAdapter()
sessions = adapter.ingest(FIXTURE_DIR, [...globs...])
result = [s.model_dump(mode="json") for s in sessions]
for d in result:
    d["ingest_key"] = None
Path("expected.json").write_text(
    json.dumps(result, indent=2, ensure_ascii=False) + "\n"
)
```

All expected.json files must have `ingest_key` set to `null` (not omitted) for consistency.

## Required Test Coverage for Every Adapter

When adding or modifying an adapter, tests must verify both ingestion idempotency and
`purge_ingested_source` behavior:

- **Idempotency:** first `ingest_source(<adapter>, config)` inserts one or more sessions,
    second call returns `0`.
- **Purge-ingested:** after ingestion, `purge_ingested_source(<adapter>, config)` deletes
    exactly ingested sessions, and a second call returns `0`.
- **Manual-session safety:** at least one test must confirm purge keeps manually created
    sessions (`ingest_key = None`).

Prefer adding these checks to shared parametrized tests in `tests/src/llm_tracer/test_ingest.py`
so new adapters inherit the same guarantees automatically.
