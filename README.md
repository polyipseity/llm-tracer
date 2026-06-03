# llm-tracer

Capture, store, review, and publish LLM conversation logs.

It provides one pipeline:

1. Ingest chat sessions from supported sources (VS Code Copilot Chat,
   LM Studio, OpenCode, Pi Coding Agent, Claude Code, Codex, oterm, Ollama).
2. Store each session as private JSON for manual review/redaction.
3. Sanitize PII/secrets and publish Parquet datasets.
4. Optionally sync published artifacts to Hugging Face.

For contributor and agent workflow policy, see `AGENTS.md`.

## Workflow

```text
init          — set up a traces repository
  │
  ▼
ingest       — pull chat logs from a source (vscode, lmstudio, opencode, …)
  │
  ├─ ingest --purge — purge ingested sessions from a source
  │
  ▼
review       — interactively accept/reject unreviewed sessions
  │
  ├─ decide  — record individual decisions without the interactive prompt
  │
  ▼
sanitize     — scan private sessions for secrets (with --apply to redact)
  │
  ▼
publish      — scrub PII/secrets, write public Parquet partitions
  │
  ├─ [--commit]  — commit the traces repo
  ├─ [--push]    — push to remote
  │
  ▼
sync         — upload changed artifacts to Hugging Face

── data subcommands ───────────────────────────────────────
data pack          — compress decided JSON into Parquet
data unpack        — restore packed Parquet back to JSON
data reingest      — reprocess private data (attachment policy)
data rebuild-views — rebuild tag symlink views
```

**Possible paths:**

- **Minimal**: `init → ingest → publish --commit` (uses `default_publish_decision` for chats without explicit decisions).
- **Reviewed**: `init → ingest → review → decide → publish --commit --push`.
- **Storage-conscious**: add `data pack` between `decide`/`sanitize` and `publish` to replace individual JSON decision files with compact Parquet partitions.
- **Incremental**: `ingest` is idempotent — re-run it anytime to pull new chats without duplicating existing ones. Likewise `publish` and `sync` only process changed content.
- **Cleanup**: `ingest --purge --source <name>` deletes privately stored sessions from a given source while preserving manually-authored ones.

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

- macOS (Stable): `~/Library/Application Support/Code/User/workspaceStorage/`,
  `~/Library/Application Support/Code/User/globalStorage/emptyWindowChatSessions/`,
  `~/Library/Application Support/Code/User/globalStorage/transferredChatSessions/`.
- macOS (Insiders): same paths under `Code - Insiders`.
- Linux (Stable): `~/.config/Code/User/workspaceStorage/`,
  `~/.config/Code/User/globalStorage/emptyWindowChatSessions/`,
  `~/.config/Code/User/globalStorage/transferredChatSessions/`.
- Linux (Insiders): same paths under `Code - Insiders`.
- Windows (Stable): `%APPDATA%\Code\User\workspaceStorage\`,
  `%APPDATA%\Code\User\globalStorage\emptyWindowChatSessions\`,
  `%APPDATA%\Code\User\globalStorage\transferredChatSessions\`.
- Windows (Insiders): same paths under `Code - Insiders`.

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

- macOS, Linux, Windows: `~/.pi/agent/`

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

- macOS: `~/Library/Application Support/oterm/`
- Linux: `~/.local/share/oterm/`
- Windows: `%APPDATA%\oterm\`

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

You can scope review by time and tags:

```sh
llm-tracer review --on-date 2026-05-28
llm-tracer review --from-date 2026-05-01 --to-date 2026-05-31
llm-tracer review --from-datetime 2026-05-28T10:00:00Z --to-datetime 2026-05-28T12:00:00Z
llm-tracer review --tag 'import/id/vscode/*'
llm-tracer review --tag 'import/**' --tag 'seed/*'
```

Tag patterns use slash-aware globbing: `*` matches one level; `**` matches
recursively across levels.

### Record a single decision

```sh
llm-tracer decide --chat-id <id> --decision accepted [--reason "looks good"]
```

Stores one `accepted`, `rejected`, or `undecided` decision in
`data/decisions/YYYY/MM/DD/part-*.jsonl` without launching the interactive
session. Re-deciding the same `chat_id` replaces its previous decision row.

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

### Sanitize private data

```sh
llm-tracer sanitize
llm-tracer sanitize --apply
```

By default, runs detect-secrets scan on all private sessions and prints a
report summary. With `--apply`, also applies Phase A (SecretStore) redaction
to all private sessions.

### Data management subcommands

Manage private trace data (pack, unpack, reingest, rebuild views).

```sh
llm-tracer data pack
llm-tracer data unpack --chat-id <id> [--chat-id <id2> ...]
llm-tracer data unpack --all
llm-tracer data reingest [--attachment-policy <policy>]
llm-tracer data rebuild-views
```

- **pack** — Compress decided (accepted/rejected) private chats from individual
  JSON files into compact Parquet partitions.
- **unpack** — Restore packed chats from Parquet back to individual JSON files.
  Specify one or more `--chat-id` or use `--all`. Leaves Parquet intact.
- **reingest** — Reprocess private chat data with an attachment policy.
- **rebuild-views** — Rebuild symlink views for private chats grouped by tag
  hierarchy.

## Expected traces repository layout

`llm-tracer init` expects (and idempotently maintains) this repository layout:

```text
data/
├── .gitignore
│   └── /private/ # private subtree stays untracked
├── chats/
│   └── YYYY/MM/DD/part-*.parquet # sanitized published chat partitions
├── decisions/
│   └── YYYY/MM/DD/part-*.jsonl # one latest decision row per chat_id
├── indexes/
│   ├── publish.parquet # publish idempotency index
│   └── hugging_face_sync.parquet # sync idempotency index
└── private/
    ├── chats/
    │   └── YYYY/MM/DD/HHMMSS_ffffff-{chat_id}.json # private normalized chat JSON
    └── views/
        └── by_tag/<tag-path>/<chat_id>.json -> ../../../chats/... # symlink by tag hierarchy
```

### Index files (full list)

- `data/indexes/publish.parquet`: latest published chat content hashes
    (`chat_id` -> `content_hash`) used by `publish` idempotency checks.
- `data/indexes/hugging_face_sync.parquet`: latest uploaded artifact hashes
    (`artifact_path` -> `content_hash`) used by `sync` idempotency checks.

Decisions are not stored in `data/indexes/`; they are stored in
`data/decisions/YYYY/MM/DD/part-*.jsonl`.

## Tag hierarchy

Tags are slash-delimited paths. Adapters always emit normalized `import/*` tags:

- `import/id/{adapter}/{source-id}` - unique source record identity
- `import/title/{title}` - normalized title when present
- `import/workspace/{folder}` - workspace/project context when present

`{adapter}` is one of: `claude_code`, `codex`, `local`, `lmstudio`, `ollama`,
`opencode`, `oterm`, `pi_coding_agent`, `vscode`.

You can also add any custom tags (for example `seed/demo`, `manual/test`,
`debugging/python`). All tags are validated, deduplicated, and sorted
deterministically before storage.

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
