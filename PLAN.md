# System Specification: Decoupled AI Chat Pipeline (Single Data Repo with Private Subtree)

## Overview

This specification document defines a decoupled architecture where `llm-tracer` writes into a single `llm-traces` data repository that contains both private (git-ignored) and public (tracked) datasets under `data/`. It avoids Git LFS by date partitioning plus chunk splitting capped at 10 MB per tracked file. It also requires strict idempotency across ingest, publish, and Hugging Face sync operations.

---

## 1. Architecture Components

```text
┌────────────────────────────────────────────────────────┐
│                   1. llm-tracer                        │
│               (Public GitHub Code Repo)                │
│  - Python CLI Core    - Pydantic Schemas               │
│  - Ingestion Adapters  - Presidio Scrubbing Rules      │
└───────────────────────────┬────────────────────────────┘
                            │
       1. Ingests local files & filters structural bloat
                            ▼
┌────────────────────────────────────────────────────────┐
│                 2. llm-traces                          │
│   (GitHub Data Repo: public tracked + private ignored) │
│  - data/private/** (ignored by data/.gitignore)        │
│  - data/chats/YYYY/MM/DD/part-*.parquet                │
│  - data/decisions/, data/indexes/, llm-tracer.toml     │
│  - Small files, standard Git tracking, clean diffs     │
└────────────────────────────────────────────────────────┘

```

* **Repository 1: `llm-tracer` (Public GitHub Code Repo):** Contains zero chat data. Stores parser logic, schemas, ingestion adapters, CLI, and Microsoft Presidio configurations.
* **Repository 2: `llm-traces` (GitHub Data Repo):** A dedicated data repository used by `llm-tracer` for both unredacted and sanitized data. Private data must live only under `data/private/` and be ignored from Git. Public sanitized artifacts and operational state are tracked.

Boundary rule: this `llm-tracer` code repository must not pre-create or version `llm-traces` data folders/files. Instead, `llm-tracer` must create and manage the required structure inside the configured `llm-traces` repository at runtime/bootstrap.

Configuration for runtime behavior, output layout, publish targets, and decision policy should be stored in a single versioned file in `llm-traces` (`llm-tracer.toml`) and passed explicitly to `llm-tracer`.

### 1.1 Minimal Recommended Folder Layout

Use `data/` as the canonical data root.

Data repo (`llm-traces`) layout:

* `data/.gitignore` — must ignore the private subtree:
  * `/private/`
* `data/private/chats/YYYY/MM/DD/part-*.jsonl` — unredacted canonical chats (never tracked).
* `data/private/ingest.parquet` — private idempotent ingest index (`chat_id`, `ingest_key`; never tracked).
* `data/chats/YYYY/MM/DD/part-*.parquet` — sanitized published chats (tracked).
* `data/decisions/YYYY/MM/DD/part-*.jsonl` — accepted/rejected decisions (tracked, source of truth).
* `data/indexes/publish.parquet` — publish idempotency index (tracked).
* `data/indexes/hugging_face_sync.parquet` — Hugging Face sync idempotency index (tracked).
* `data/indexes/decision_latest.parquet` — optional derived latest-decision lookup by `chat_id` (tracked).
* `llm-tracer.toml` — single runtime configuration file (tracked).

Minimality rule: keep only these stable roots under `data/` unless a new durable requirement appears: `chats/`, `private/`, `decisions/`, `indexes/`.

Implementation notes:

* `llm-tracer` must ensure `data/.gitignore` exists in the target `llm-traces` repo before writing private data.
* Users may replace `data/private` with a symlink to any local path.
* Public tracked files must be chunk-split so each file stays below 10 MB.
* Structure/bootstrap operations must be idempotent (safe to run repeatedly with no destructive side effects).

---

## 2. Target Unified Schema (`src/core/schema.py`)

All adapters must normalize source data into this schema using Pydantic v2.

```python
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str = Field(..., description="System, user, assistant, or tool")
    content: str = Field(..., description="Raw markdown message payload string")
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatSession(BaseModel):
    id: str = Field(..., description="Deterministic SHA256 hash of canonicalized thread content")
    source: str = Field(..., description="Source slug: vscode-copilot, lm-studio, pi-agent, etc.")
    timestamp: datetime = Field(..., description="ISO 8601 UTC execution timestamp with timezone info")
    model: str = Field(..., description="Target model identifier string")
    messages: List[Message]
    tags: List[str] = Field(default_factory=list, description="Hierarchical tags separated by '/'")

```

### 2.1 Identifier, Tag, and Idempotency Contract

To guarantee idempotency, `llm-tracer` must use deterministic identifiers and upsert behavior:

* **`chat_id` (`ChatSession.id`)**: SHA256 over canonicalized session content. This is the primary identity key across private and public datasets plus Hugging Face sync indexes.
* **`source_record_id`** (adapter-level metadata): stable source-native identifier when available (for example, upstream conversation id).
* **`ingest_key`**: deterministic key for ingestion lineage (for example, SHA256 of `source + source_record_id + normalized_source_path`).

Idempotency rules:

1. Re-importing the same source data must not create duplicate private records for the same `chat_id`.
2. Re-running sanitize/publish must upsert by `chat_id` into deterministic date partitions.
3. Re-running Hugging Face sync must upload only changed artifacts (detected via sync index content hashes).

Required indexes/state in `llm-traces`:

* `llm-tracer.toml` — canonical runtime configuration.
* `data/indexes/publish.parquet` — `chat_id`-keyed publish index and content hashes.
* `data/indexes/hugging_face_sync.parquet` — artifact/hash/revision tracking for idempotent Hugging Face sync.
* `data/decisions/YYYY/MM/DD/part-*.jsonl` — append-only accepted/rejected chat decisions (canonical event log).

Tag contract (applies to both private and public stores):

* Tags are hierarchical paths with separator `/`.
* Each path component must be non-empty and must not contain `/` or `\\`.
* Any other character is allowed.
* Tags are normalized and deduplicated before persistence.

Default import tagging:

* During ingest, each imported chat gets default tag `import/<relative-folder-path>`.
* `<relative-folder-path>` is the path of the folder containing the chat file, relative to the configured import root.
* Imported tags are merged (set union) with existing tags on idempotent upsert.

---

## 3. Operational Pipeline Workflow

The pipeline coordinates local processing and public publishing without versioning private raw data.

1. **Ingest & Normalize (Local De-bloat).**
    Parse raw application folders (for example, `~/.lmstudio/conversations/`), strip structural metadata bloat, drop failed/empty sessions, validate against the Pydantic schema, attach default `import/<relative-folder-path>` tags, and upsert unique sessions into `llm-traces/data/private/chats/YYYY/MM/DD/part-*.jsonl`.

2. **Scrub & Partition (Presidio Processing).**
    Stream private files through Microsoft Presidio using `config/presidio_rules.yaml` and custom recognizers/patterns as needed. Replace detected secrets/PII with stable placeholders (for example, `<REDACTED_SECRET>`), preserve tags, partition by date, and upsert outputs by `chat_id` into `data/chats/YYYY/MM/DD/part-*.parquet`.

3. **Standard Git Push (Public Data Repo Only).**
    Run Git operations inside the local clone of `llm-traces` to stage, commit, and push sanitized changes plus updated indexes and `llm-tracer.toml`.

4. **Optional Hugging Face Sync (Public Sanitized Data Only).**
    Mirror sanitized partitions from `llm-traces` to a Hugging Face dataset repository using explicit credentials/config supplied by the user and skip unchanged artifacts via index hash checks.

5. **Decision Logging (Accepted/Rejected).**
    Persist every decision event in `llm-traces/data/decisions/YYYY/MM/DD/part-*.jsonl` with deterministic `decision_event_id`, `chat_id`, `decision` (`accepted` or `rejected`), timestamp, and optional rationale metadata. Optionally materialize `data/indexes/decision_latest.parquet` for fast current-state lookup.

---

## 4. Coding Agent Implementation Tasks

### Task 1: Project Setup & Core Logic

Build a structured Python CLI inside the **Public Code Repository** (`llm-tracer`) using `click` or `typer`.

* **Dependencies:** `pydantic`, `presidio-analyzer`, `presidio-anonymizer`, `pandas`, `pyarrow`.

Add a repository bootstrap routine (for example, `init-traces-repo`) that creates/validates the `llm-traces` layout (`data/chats`, `data/decisions`, `data/indexes`, `data/private/chats`) and writes `data/.gitignore` with `/private/` if missing.

### Task 2: Implement Ingestion Adapters

Create an extensible adapter framework under `src/adapters/` supporting:

* `lmstudio.py`: Reads and normalizes logs from local LM Studio conversation files.
* `copilot.py`: Maps exported VS Code Copilot chat/session history structures.
* `pi_agent.py`: Normalizes execution traces.

Implement a `BaseAdapter` abstract class with an `.ingest()` method returning `list[ChatSession]`.

Enforce tag normalization/validation and automatic default import tagging (`import/<relative-folder-path>`) during ingest.

### Task 3: Build the Partitioned Sanitization Engine

Inside `src/core/engine.py`, implement logic that:

1. Streams unredacted JSONL lines from `data/private/chats/**`.
2. Anonymizes message text layers via Microsoft Presidio.
3. Converts sanitized records into a `pandas.DataFrame`.
4. Extracts year/month/day from `timestamp`.
5. Writes compact date partitions using `df.to_parquet()` into `data/chats/YYYY/MM/DD/part-*.parquet`.

Apply deterministic deduplication using the same canonicalization strategy used to generate `ChatSession.id`.

Use explicit runtime configuration loading (for example, from `--config /path/to/llm-traces/llm-tracer.toml`) so source import roots, repo paths, and optional Hugging Face targets are centrally managed and never hardcoded.

Ensure publish is idempotent by maintaining `data/indexes/publish.parquet` keyed by `chat_id` and sanitized content hash.

### Task 4: Automate Public Data Git Lifecycle

Add a sync feature using Python `subprocess` to stage changed files, avoid empty commits, and push updates from the public data repository clone.

```python
import subprocess
from pathlib import Path


def sync_public_repo(repo_path: Path, commit_message: str) -> None:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )

    if not status.stdout.strip():
        return

    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", commit_message], cwd=repo_path, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=repo_path, check=True)

```

### Task 5: Add Optional Hugging Face Dataset Sync

Add an optional publish step that syncs sanitized date partitions from `llm-traces` to a Hugging Face dataset repository (for example, via `huggingface_hub`). This step must be opt-in, must never read from or upload anything under `data/private/`, and must use `data/indexes/hf_sync.parquet` for idempotent re-sync behavior.

### Task 6: Store Full Public Operational State

Persist operational state required by `llm-tracer` in `llm-traces`, including:

* `llm-tracer.toml` (single runtime configuration file)
* `data/decisions/` (accepted/rejected chat decisions)
* `data/indexes/` (publish and Hugging Face sync idempotency indexes)

Public store state must be sufficient for deterministic reruns of publish/sync workflows.

---

## 5. Execution Interface Requirements

The CLI must explicitly map source and destination paths across the decoupled components.

```bash
# Optional bootstrap: create/validate llm-traces folder layout and data/.gitignore
uv run python src/main.py init-traces-repo --repo-dir /path/to/llm-traces

# Step 1: Ingest from source, remove structural bloat, append into date-partitioned private store
uv run python src/main.py ingest --source lmstudio --config /path/to/llm-traces/llm-tracer.toml

# Step 2: Publish from data/private to tracked data/chats using date folders and chunked parts
uv run python src/main.py publish --config /path/to/llm-traces/llm-tracer.toml \
                                  --commit-msg "archive: update logs for 2026-05-23"

# Optional: record a review decision for a specific chat id
uv run python src/main.py decide --config /path/to/llm-traces/llm-tracer.toml \
                                 --chat-id <CHAT_ID> --decision accepted --reason "useful for benchmark set"

# Step 3 (optional): Mirror sanitized public data to Hugging Face dataset repo
uv run python src/main.py sync-hugging-face --config /path/to/llm-traces/llm-tracer.toml

```

---

## 6. Verification Checklist for Agent Completion

Before completion, verify that:

1. `pytest` passes adapter and engine tests using mock source data.
2. A dummy secret in input text (for example, `sk-or-v1-a1b2c3d4...`) is replaced by `<REDACTED_SECRET>` in sanitized outputs.
3. No hardcoded machine-specific paths are used for import roots or repository targets.
4. Both private and public data are partitioned as `YYYY/MM/DD/` folders with split `part-*` files.
5. Tracked files remain below the 10 MB target chunk size (and therefore below GitHub's 100MB hard limit) without Git LFS.
6. Only public data in `llm-traces` is version-controlled; `data/private/` is always ignored by `data/.gitignore`.
7. Hugging Face sync (when enabled) publishes only sanitized data.
8. Re-running ingest, publish, or sync-hugging-face without new data is a no-op (no duplicate records and no redundant uploads).
9. Tag validation is enforced, tags are preserved through publish, and default `import/<relative-folder-path>` tags are present.
10. `llm-traces` stores complete operational state required by `llm-tracer` (`llm-tracer.toml`, `data/decisions/**`, and `data/indexes/**`).
11. Tracked `data/chats/**` and `data/decisions/**` files are chunked to stay under 10 MB each.
12. Running the bootstrap routine repeatedly is idempotent and preserves existing data.
