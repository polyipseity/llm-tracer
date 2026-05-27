# llm-tracer

Capture, store, review, and publish LLM conversation logs.

llm-tracer ingests chat sessions from multiple sources (VS Code Copilot Chat,
LM Studio, OpenCode, Pi Coding Agent, Claude Code, Codex, oterm, Ollama), stores each session as an individual
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

Shell completion works the same for normal and editable installs, including
`uv tool install .` and `uv tool install --editable .`.

```sh
llm-tracer completion install zsh
llm-tracer completion install bash
llm-tracer completion install fish
llm-tracer completion install pwsh
```

To inspect or manually place a script instead, use `completion show`:

```sh
llm-tracer completion show zsh
llm-tracer completion show bash
llm-tracer completion show fish
llm-tracer completion show powershell
```

## Configuration

Create an `llm-tracer.toml` in your current working directory (or use
the `init` command to scaffold one there while pointing `repo_dir` at a
separate traces repository):

```toml
repo_dir = "."
chunk_size_bytes = 1_000_000    # 1 MB per public Parquet partition
default_publish_decision = "reject"  # policy for chats without an explicit decision

[sources.vscode]
# roots auto-detected per platform; override only if needed

[sources.lmstudio]
# roots auto-detected to ~/.lmstudio/conversations/

[hugging_face]
enabled = false
repo_id = "your-org/your-dataset"
token_env_var = "HUGGING_FACE_TOKEN"
```

## Sources

Each source adapter discovers chat files automatically without requiring a
`roots` value in the config. Set `roots` to override default locations.

### `lmstudio`

LM Studio conversation history.

| Platform                | Default path                   |
| ----------------------- | ------------------------------ |
| macOS, Linux, Windows   | `~/.lmstudio/conversations/`   |

### `vscode`

VS Code Copilot Chat sessions (JSONL mutation-log format, VS Code ≥ 1.99).

| Platform   | Edition    | Default paths                                                         |
| ---------- | ---------- | --------------------------------------------------------------------- |
| macOS      | Stable     | `~/Library/Application Support/Code/User/workspaceStorage/`           |
|            |            | `~/Library/Application Support/Code/User/globalStorage/emptyWindowChatSessions/` |
|            |            | `~/Library/Application Support/Code/User/globalStorage/transferredChatSessions/` |
| macOS      | Insiders   | same paths under `Code - Insiders`                                    |
| Linux      | Stable     | `~/.config/Code/User/workspaceStorage/`                               |
|            |            | `~/.config/Code/User/globalStorage/emptyWindowChatSessions/`          |
|            |            | `~/.config/Code/User/globalStorage/transferredChatSessions/`          |
| Linux      | Insiders   | same paths under `Code - Insiders`                                    |
| Windows    | Stable     | `%APPDATA%\Code\User\workspaceStorage\`                            |
|            |            | `%APPDATA%\Code\User\globalStorage\emptyWindowChatSessions\`      |
|            |            | `%APPDATA%\Code\User\globalStorage\transferredChatSessions\`      |
| Windows    | Insiders   | same paths under `Code - Insiders`                                    |

Per-workspace sessions are stored as
`workspaceStorage/{workspace-hash}/chatSessions/{session-uuid}.jsonl`.
Empty-window and transferred sessions are stored directly in their named
directories.

### `opencode`

OpenCode session history (JSON file format; predates the SQLite migration in
February 2026).

| Platform              | Default path                         |
| --------------------- | ------------------------------------ |
| macOS, Linux, Windows | `~/.local/share/opencode/storage/`   |

OpenCode uses XDG Base Directory conventions on all platforms
(`XDG_DATA_HOME/opencode/storage`), which resolves to `~/.local/share` when
`XDG_DATA_HOME` is not set.

### `pi_coding_agent`

Pi Coding Agent execution traces (format reverse-engineered; no public
documentation).

| Platform         | Default paths                                           |
| ---------------- | ------------------------------------------------------- |
| macOS, Linux, Windows | `~/.pi/agent/`                                   |

### `claude_code`

Claude Code project transcripts (JSONL event logs).

| Platform              | Default path                |
| --------------------- | --------------------------- |
| macOS, Linux, Windows | `~/.claude/projects/`       |

### `codex`

Codex rollout transcripts (JSONL event logs).

| Platform              | Default path                 |
| --------------------- | ---------------------------- |
| macOS, Linux, Windows | `~/.codex/sessions/`         |

### `oterm`

oterm local SQLite storage (`store.db` with `chat` + `message` tables).

| Platform              | Default paths                            |
| --------------------- | ---------------------------------------- |
| macOS                 | `~/Library/Application Support/oterm/`   |
| Linux                 | `~/.local/share/oterm/`                  |
| Windows               | `%APPDATA%\oterm\`                      |

### `ollama`

Ollama CLI prompt history (`history` file; prompt-only import).

| Platform              | Default path          |
| --------------------- | --------------------- |
| macOS, Linux, Windows | `~/.ollama/`          |

### `local`

Scans a user-specified directory and delegates each file to the best-matching
source adapter. **Requires explicit `roots`** — there is no default path.

```toml
[sources.local]
roots = ["/path/to/exports", "/another/path/to/exports"]
```

## Usage

All commands accept `--help` for full option documentation.
`--config` defaults to `llm-tracer.toml` in the current directory.

### Initialize a traces repository

```sh
llm-tracer init /path/to/traces-repo
```

Creates the expected repository layout idempotently and writes
`./llm-tracer.toml` in the current working directory with `repo_dir` set to the
path you passed.

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
