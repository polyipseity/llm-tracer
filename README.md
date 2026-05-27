# llm-tracer

Capture, store, review, and publish LLM conversation logs.

llm-tracer ingests chat sessions from multiple sources (VS Code Copilot Chat,
LM Studio, OpenCode, Pi Coding Agent), stores each session as an individual
JSON file in a private directory for easy manual review and redaction, scrubs
PII and secrets during a sanitize step, and writes clean Parquet datasets for
public archival — with optional sync to a Hugging Face dataset repository.

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
repo_dir = "."
chunk_size_bytes = 1_000_000    # 1 MB per public Parquet partition
default_publish_decision = "reject"  # policy for chats without an explicit decision

[sources.vscode]
# root auto-detected per platform; override only if needed

[sources.lmstudio]
# root auto-detected to ~/.lmstudio/conversations/

[hugging_face]
enabled = false
repo_id = "your-org/your-dataset"
token_env_var = "HUGGING_FACE_TOKEN"
```

## Sources

Each source adapter discovers chat files automatically without requiring a
`root` in the config. Set `root` to override the default location.

### `lmstudio`

LM Studio conversation history.

| Platform | Default path |
|---|---|
| macOS, Linux, Windows | `~/.lmstudio/conversations/` |

### `vscode`

VS Code Copilot Chat sessions (JSONL mutation-log format, VS Code ≥ 1.99).

| Platform | Edition | Default paths |
|---|---|---|
| macOS | Stable | `~/Library/Application Support/Code/User/workspaceStorage/` |
| | | `~/Library/Application Support/Code/User/globalStorage/emptyWindowChatSessions/` |
| | | `~/Library/Application Support/Code/User/globalStorage/transferredChatSessions/` |
| macOS | Insiders | same paths under `Code - Insiders` |
| Linux | Stable | `~/.config/Code/User/workspaceStorage/` |
| | | `~/.config/Code/User/globalStorage/emptyWindowChatSessions/` |
| | | `~/.config/Code/User/globalStorage/transferredChatSessions/` |
| Linux | Insiders | same paths under `Code - Insiders` |
| Windows | Stable | `%APPDATA%\Code\User\workspaceStorage\` |
| | | `%APPDATA%\Code\User\globalStorage\emptyWindowChatSessions\` |
| | | `%APPDATA%\Code\User\globalStorage\transferredChatSessions\` |
| Windows | Insiders | same paths under `Code - Insiders` |

Per-workspace sessions are stored as
`workspaceStorage/{workspace-hash}/chatSessions/{session-uuid}.jsonl`.
Empty-window and transferred sessions are stored directly in their named
directories.

### `opencode`

OpenCode session history (JSON file format; predates the SQLite migration in
February 2026).

| Platform | Default path |
|---|---|
| macOS, Linux, Windows | `~/.local/share/opencode/storage/` |

OpenCode uses XDG Base Directory conventions on all platforms
(`XDG_DATA_HOME/opencode/storage`), which resolves to `~/.local/share` when
`XDG_DATA_HOME` is not set.

### `pi_coding_agent`

Pi Coding Agent execution traces (format reverse-engineered; no public
documentation).

| Platform | Default paths |
|---|---|
| macOS | `~/.pi-agent/`, `~/Library/Application Support/PiAgent/` |
| Linux, Windows | `~/.pi-agent/` |

### `local`

Scans a user-specified directory and delegates each file to the best-matching
source adapter. **Requires an explicit `root`** — there is no default path.

```toml
[sources.local]
root = "/path/to/exports"
```

## Usage

All commands accept `--help` for full option documentation.
`--config` defaults to `llm-tracer.toml` in the current directory.

### Initialize a traces repository

```sh
llm-tracer init-traces-repo /path/to/traces-repo
```

Creates the expected directory layout idempotently.

### Ingest a source

```sh
llm-tracer ingest --source vscode
```

Reads raw chat logs from the configured source, normalizes them, and stores
new sessions as individual JSON files under `data/private/chats/`.

### Review sessions interactively

```sh
llm-tracer review
```

Opens an interactive terminal prompt presenting each unreviewed chat with a
message preview. Keys: `a` accept · `r` reject · `u` undecided · `s` skip ·
`q` quit.

### Record a single decision

```sh
llm-tracer decide --chat-id <id> --decision accepted [--reason "looks good"]
```

Appends one `accepted`, `rejected`, or `undecided` annotation to the decision
index without launching the interactive session.

### Publish sanitized data

```sh
llm-tracer publish [--commit] [--push]
```

Scrubs PII and secrets, then writes public Parquet partitions. Only chats with
an `accepted` decision (or matching `default_publish_decision`) are included.
Pass `--commit` to commit the data repo and `--push` to push.

### Sync to remote backends

```sh
llm-tracer sync
```

Uploads changed Parquet files to all enabled remote backends (currently Hugging
Face dataset repositories). Requires the token in the environment variable
named by `token_env_var` (default: `HUGGING_FACE_TOKEN`).

### Purge an ingested source

```sh
llm-tracer purge-ingested --source vscode
```

Deletes all privately-stored sessions originally ingested from the given source,
along with their ingest index entries.

## Architecture

```text
src/llm_tracer/
├── cli.py          — Typer CLI entry point
├── config.py       — Configuration loading (llm-tracer.toml)
├── bootstrap.py    — Traces-repo scaffolding
├── ingest.py       — Ingestion orchestration
├── decisions.py    — Decision event logging
├── review.py       — Interactive review session
├── schema/         — Canonical Pydantic data models (v1)
├── storage/        — JSON / Parquet partition helpers
├── sanitize/       — PII-scrubbing and publish pipeline
├── sync/           — git and Hugging Face sync backends
├── utils/          — Hashing and tag-normalization helpers
└── adapters/       — Per-source adapters (vscode, lmstudio, opencode, …)
```
