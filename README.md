# llm-tracer

Capture, store, and selectively publish LLM conversation logs.

llm-tracer ingests chat sessions from multiple sources (VS Code Copilot,
LM Studio, OpenCode, Pi Coding Agent), stores them in private JSONL
partitions, scrubs PII and secrets during a sanitize step, and writes
clean Parquet datasets for public archival — with optional sync to a
Hugging Face dataset repository.

## Installation

```sh
uv tool install llm-tracer
```

Or as a project dependency:

```sh
uv add llm-tracer
```

## Configuration

Create an `llm-tracer.toml` in your traces repository (or use
`init-traces-repo` to scaffold one):

```toml
repo_dir = "/path/to/traces-repo"
chunk_size_bytes = 1_000_000   # 1 MB per chunk

[sources.vscode]
paths = ["/path/to/vscode/chat/logs"]

[sources.lmstudio]
paths = ["/path/to/lmstudio/chat/logs"]
```

## Usage

All commands accept `--help` for full option documentation.

### Initialize a traces repository

```sh
llm-tracer init-traces-repo /path/to/traces-repo
```

Creates the expected directory layout idempotently.

### Ingest a source

```sh
llm-tracer ingest --source vscode --config llm-tracer.toml
```

Reads raw chat logs from the configured source, normalizes them, and
appends new sessions to the private JSONL store.

### Publish sanitized data

```sh
llm-tracer publish --config llm-tracer.toml [--commit] [--push]
```

Scrubs PII and secrets, then writes public Parquet partitions.
Pass `--commit` to auto-commit the data repo and `--push` to push.

### Record a review decision

```sh
llm-tracer decide --config llm-tracer.toml \
  --chat-id <id> --decision accepted [--reason "looks good"]
```

Appends an accepted/rejected annotation to the decision index.

### Sync to Hugging Face

```sh
llm-tracer sync-hugging-face --config llm-tracer.toml
```

Uploads changed Parquet files to the configured Hugging Face dataset
repository. Requires `HF_TOKEN` in the environment.

### Purge an imported source

```sh
llm-tracer purge-imported --source vscode --config llm-tracer.toml
```

Deletes all privately-stored sessions that were originally imported from
the given source, rewriting both the JSONL store and the ingest index.

## Architecture

```text
src/llm_tracer/
├── cli.py          — Typer CLI entry point
├── config.py       — Configuration loading (llm-tracer.toml)
├── bootstrap.py    — Traces-repo scaffolding
├── ingest.py       — Ingestion orchestration
├── decisions.py    — Decision event logging
├── schema/         — Canonical Pydantic data models (v1)
├── storage/        — JSONL / Parquet partition helpers
├── sanitize/       — PII-scrubbing and publish pipeline
├── sync/           — git and Hugging Face sync backends
├── utils/          — Hashing and tag-normalization helpers
└── adapters/       — Per-source adapters (vscode, lmstudio, opencode, …)
```
