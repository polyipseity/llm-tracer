---
description: "Use when creating or updating adapter example scripts in examples/adapters/. Enforces that every adapter example must include a corresponding expected.json fixture and verify output against it in main()."
name: "Adapter Example Verification Pattern"
applyTo: "examples/adapters/*.py"
---

# Adapter Example Verification Pattern

Every adapter example must verify output against `expected.json` using the shared
`verify_against_expected()` helper from `examples/adapters/_common.py`.

## Fixture Structure

Each adapter fixture (`examples/fixtures/<adapter_name>/`) must include:

- Data files that the adapter ingests
- **expected.json** at root: list of `ChatSession` objects (via `model_dump(mode="json")`)

Include representative **rich payloads** in every fixture:

- Attachments or file-like metadata
- Images or image-like blocks
- Embeddings or vector-like metadata
- Unknown/extra fields that should be safely ignored

This ensures adapters handle production-like data diversity.

## Example Script Pattern

```python
from examples.adapters._common import verify_against_expected

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "<name>"
EXPECTED_JSON = FIXTURE_DIR / "expected.json"

# In main():
sessions = adapter.ingest(...)
verify_against_expected(sessions, EXPECTED_JSON, skip_fields=["ingest_key"])
```

**Timestamp handling:**

- Stable adapters (claude_code, codex, lmstudio, vscode, opencode, pi_coding_agent, local):
  Skip only `ingest_key`.
- Unstable adapters (ollama, oterm): Skip both `ingest_key` and `timestamp`.

## Regenerating expected.json

```python
adapter = SomeAdapter()
sessions = adapter.ingest(FIXTURE_DIR, [...globs...])
result = [s.model_dump(mode="json") for s in sessions]
for d in result:
    d["ingest_key"] = None  # Ensure null, not omitted
Path("expected.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
```
