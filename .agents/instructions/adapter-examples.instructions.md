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

- Resolve fixture paths relative to `examples/fixtures/<adapter_name>/`.
- In `main()`, ingest fixture data and call `verify_against_expected(...)`.
- Keep skip fields explicit in each example (`ingest_key` for stable adapters;
  add `timestamp` for unstable adapters).

**Timestamp handling:**

- Stable adapters (claude_code, codex, lmstudio, vscode, opencode, pi_coding_agent, local):
  Skip only `ingest_key`.
- Unstable adapters (ollama, oterm): Skip both `ingest_key` and `timestamp`.

## Regenerating expected.json

- Rebuild fixture output by ingesting fixture data and serializing each session
  with `model_dump(mode="json")`.
- Normalize `ingest_key` to JSON `null` before writing `expected.json`.
- Keep JSON UTF-8, pretty-printed, and newline-terminated for stable diffs.
