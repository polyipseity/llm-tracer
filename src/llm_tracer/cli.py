"""Typer-based CLI for ingest, publish, decision logging, and syncing."""

import json
import re
from pathlib import Path

import typer

from llm_tracer.adapters import ADAPTERS
from llm_tracer.bootstrap import bootstrap_traces_repo
from llm_tracer.completion import (
    CompletionShell,
    install_shell_completion,
    render_shell_completion,
)
from llm_tracer.config import default_config_template, load_config
from llm_tracer.decisions import record_decision
from llm_tracer.ingest import ingest_source, purge_ingested_source
from llm_tracer.reprocess import AttachmentPolicy, reprocess_private_data
from llm_tracer.review import interactive_review
from llm_tracer.sanitize import (
    pack_private_chats,
    publish_sanitized,
    sanitize_private,
    unpack_private_chats,
)
from llm_tracer.sanitize.scanner import ScannerConfig, scan_sessions
from llm_tracer.sanitize.secrets import SecretStore
from llm_tracer.sync import sync_all
from llm_tracer.sync.git import sync_public_repo
from llm_tracer.utils.hashing import hash_bytes
from llm_tracer.views import rebuild_private_tag_views

"""Public symbols exported by this module."""
__all__ = ("app", "main")

"""Root Typer application instance."""
app = typer.Typer(
    add_completion=False,
    help="Decoupled LLM trace ingestion and publish pipeline.",
)

"""Typer sub-application for shell completion helpers."""
completion_app = typer.Typer(help="Generate or install shell completion scripts.")

"""Typer sub-application for secret management."""
secrets_app = typer.Typer(help="Manage known secrets for deterministic redaction.")

app.add_typer(completion_app, name="completion")
app.add_typer(secrets_app, name="secrets")

"""Default config filename created and loaded from the current directory."""
_DEFAULT_CONFIG_NAME = "llm-tracer.toml"

"""Pattern used to replace the top-level `repo_dir` assignment in TOML."""
_REPO_DIR_PATTERN = re.compile(r"(?m)^repo_dir\s*=.*$")


def _repo_dir_assignment(repo_dir: Path) -> str:
    """Return a TOML assignment line for `repo_dir`."""

    return f"repo_dir = {json.dumps(str(repo_dir))}"


def _write_or_update_init_config(config_path: Path, *, repo_dir: Path) -> None:
    """Create or update the cwd config so `repo_dir` points at the traces repo."""

    if not config_path.exists():
        config_path.write_text(
            default_config_template(repo_dir=repo_dir),
            encoding="utf-8",
        )
        return

    repo_dir_line = _repo_dir_assignment(repo_dir)
    existing = config_path.read_text(encoding="utf-8")
    updated, n_subs = _REPO_DIR_PATTERN.subn(repo_dir_line, existing, count=1)
    if n_subs == 0:
        stripped = existing.lstrip("\n")
        updated = f"{repo_dir_line}\n{stripped}" if stripped else f"{repo_dir_line}\n"
    if not updated.endswith("\n"):
        updated = f"{updated}\n"
    config_path.write_text(updated, encoding="utf-8")


@app.command("init")
def init_traces_repo(repo_dir: Path) -> None:
    """Create or validate traces repository structure and cwd config."""

    bootstrap_traces_repo(repo_dir)
    config_path = Path.cwd() / _DEFAULT_CONFIG_NAME
    _write_or_update_init_config(config_path, repo_dir=repo_dir)
    typer.echo(f"initialized traces repo layout at {repo_dir}")
    typer.echo(f"configured {config_path} with repo_dir={repo_dir}")


@app.command("ingest")
def ingest(
    source: str | None = typer.Option(
        None, help=f"Source slug to ingest. One of: {', '.join(ADAPTERS)}"
    ),
    purge: str | None = typer.Option(
        None, "--purge", help="Source slug to purge instead."
    ),
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
) -> None:
    """Ingest or purge sessions from a source."""

    runtime = load_config(config)

    if purge is not None:
        deleted = purge_ingested_source(purge, runtime)
        typer.echo(f"purge complete: deleted={deleted} source={purge}")
        links = rebuild_private_tag_views(runtime)
        typer.echo(f"private tag views rebuilt: links={links}")
        return

    if source is None:
        raise typer.BadParameter("Either --source or --purge must be provided")

    stats = ingest_source(source, runtime)
    msg = (
        f"ingest complete: source={source} "
        f"newly_inserted={stats.newly_inserted} "
        f"updated={stats.updated} "
        f"already_ingested={stats.already_ingested}"
    )
    if stats.errors:
        msg += f" errors={len(stats.errors)}"
    typer.echo(msg)
    links = rebuild_private_tag_views(runtime)
    typer.echo(f"private tag views rebuilt: links={links}")


@app.command("publish")
def publish(
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
    no_scan: bool = typer.Option(
        False, "--no-scan", help="Skip detect-secrets scanner gate."
    ),
    commit_msg: str | None = typer.Option(
        None, help="Optional commit message for data repo"
    ),
    commit: bool = typer.Option(
        False, help="Commit changed files in data repo after publish"
    ),
    push: bool = typer.Option(
        False, help="Push to remote after commit (disabled by default)"
    ),
) -> None:
    """Publish sanitized chats into tracked partitioned parquet files."""

    runtime = load_config(config)
    changed, blocked = publish_sanitized(runtime, no_scan=no_scan)
    typer.echo(f"publish complete: changed={changed} blocked={blocked}")
    if commit and changed > 0:
        message = commit_msg or "archive: update sanitized chat traces"
        committed = sync_public_repo(runtime.repo_dir, message, push=push)
        typer.echo(f"git sync complete: committed={committed} push={push}")


@app.command("decide")
def decide(
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
    chat_id: str = typer.Option(..., help="Chat identifier to annotate"),
    decision: str = typer.Option(
        ..., help="Decision value: accepted|rejected|undecided"
    ),
    reason: str | None = typer.Option(None, help="Optional decision rationale"),
) -> None:
    """Record one accepted/rejected decision event."""

    runtime = load_config(config)
    event_id = record_decision(
        config=runtime,
        chat_id=chat_id,
        decision=decision,
        reason=reason,
    )
    typer.echo(f"decision recorded: event_id={event_id}")


@app.command("sync")
def sync_command(
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
) -> None:
    """Sync sanitized public partitions to all enabled remote backends."""

    runtime = load_config(config)
    uploads = sync_all(runtime)
    typer.echo(f"sync complete: uploads={uploads}")


@app.command("sanitize")
def sanitize_command(
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Apply Phase A (SecretStore) redaction to private sessions after scanning.",
    ),
) -> None:
    """Scan private sessions for secrets and optionally apply redaction.

    By default, runs detect-secrets scan and prints a report summary.
    With --apply, also applies Phase A (SecretStore) redaction to all
    private sessions.
    """

    runtime = load_config(config)
    private_dir = runtime.repo_dir / "data/private/chats"
    from llm_tracer.storage import read_private_chats  # noqa: PLC0415

    sessions = read_private_chats(private_dir)
    scanner_config = ScannerConfig(
        report_dir=runtime.repo_dir / "data/private/reports",
    )
    reports = scan_sessions(sessions, scanner_config)
    blocked_total = sum(1 for r in reports.values() if r.blocked)
    total_findings = sum(len(r.findings) for r in reports.values())
    typer.echo(
        f"scan complete: sessions={len(reports)} "
        f"blocked={blocked_total} findings={total_findings}"
    )

    if apply:
        changed = sanitize_private(runtime)
        typer.echo(f"santize-apply complete: changed={changed}")


@app.command("review")
def review_command(
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
    on_date: str | None = typer.Option(
        None,
        "--on-date",
        help="Select chats on one date (YYYY-MM-DD, UTC).",
    ),
    from_date: str | None = typer.Option(
        None,
        "--from-date",
        help="Select chats on/after date (YYYY-MM-DD, UTC).",
    ),
    to_date: str | None = typer.Option(
        None,
        "--to-date",
        help="Select chats on/before date (YYYY-MM-DD, UTC).",
    ),
    at_datetime: str | None = typer.Option(
        None,
        "--at-datetime",
        help="Select chats at one exact datetime (ISO-8601).",
    ),
    from_datetime: str | None = typer.Option(
        None,
        "--from-datetime",
        help="Select chats on/after datetime (ISO-8601).",
    ),
    to_datetime: str | None = typer.Option(
        None,
        "--to-datetime",
        help="Select chats on/before datetime (ISO-8601).",
    ),
    tag: list[str] = typer.Option(
        [],
        "--tag",
        help=(
            "Tag glob pattern. Repeat for multiple patterns. "
            "Use * for one level and ** for recursive matching."
        ),
    ),
) -> None:
    """Interactively review and annotate pending private chats."""

    runtime = load_config(config)
    try:
        interactive_review(
            runtime,
            on_date=on_date,
            from_date=from_date,
            to_date=to_date,
            at_datetime=at_datetime,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
            tag_patterns=tuple(tag),
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error


"""Typer sub-application for data management commands."""
data_app = typer.Typer(help="Manage private trace data.")

app.add_typer(data_app, name="data")


@data_app.command("pack")
def data_pack(
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
) -> None:
    """Pack decided private chats from JSON into efficient Parquet storage."""

    runtime = load_config(config)
    packed = pack_private_chats(runtime)
    typer.echo(f"pack complete: packed={packed}")


@data_app.command("unpack")
def data_unpack(
    chat_id: list[str] = typer.Option(
        [], "--chat-id", help="Chat ID(s) to unpack. Repeatable."
    ),
    unpack_all: bool = typer.Option(False, "--all", help="Unpack all packed chats."),
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
) -> None:
    """Restore packed private chats from Parquet back to individual JSON files.

    Requires --chat-id (one or more) XOR --all. Leaves Parquet files intact.
    """

    runtime = load_config(config)

    if unpack_all and chat_id:
        raise typer.BadParameter("Cannot use both --chat-id and --all")
    if not unpack_all and not chat_id:
        raise typer.BadParameter("Must provide either --chat-id or --all")

    chat_ids: frozenset[str] | None = None if unpack_all else frozenset(chat_id)
    unpacked = unpack_private_chats(runtime, chat_ids=chat_ids)
    typer.echo(f"unpack complete: unpacked={unpacked}")


@data_app.command("reingest")
def data_reingest(
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
    attachment_policy: str | None = typer.Option(
        None,
        help=f"Attachment policy to apply. One of: {', '.join(p.value for p in AttachmentPolicy)}",
    ),
) -> None:
    """Reprocess private chat data based on attachment policy."""

    runtime = load_config(config)

    policy = None
    if attachment_policy is not None:
        try:
            policy = AttachmentPolicy(attachment_policy)
        except ValueError:
            valid_policies = ", ".join(p.value for p in AttachmentPolicy)
            raise typer.BadParameter(
                f"Invalid attachment_policy. Must be one of: {valid_policies}"
            ) from None

    try:
        processed, errors = reprocess_private_data(runtime, policy)
        msg = f"reingest complete: processed={processed}"
        if errors:
            msg += f" errors={errors}"
        typer.echo(msg)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error


@data_app.command("rebuild-views")
def data_rebuild_views(
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
) -> None:
    """Rebuild symlink views for private chats grouped by tag hierarchy."""

    runtime = load_config(config)
    links = rebuild_private_tag_views(runtime)
    typer.echo(f"private tag views rebuilt: links={links}")


@completion_app.command("show")
def show_completion_command(shell: CompletionShell) -> None:
    """Print the completion script for one shell."""

    typer.echo(render_shell_completion(shell), nl=False)


@completion_app.command("install")
def install_completion_command(shell: CompletionShell) -> None:
    """Install shell completion for one shell."""

    try:
        installed_shell, target_path = install_shell_completion(shell)
    except OSError as error:
        typer.echo(
            f"failed to install completion for {shell.value}: {error}",
            err=True,
        )
        raise typer.Exit(code=1) from error
    typer.echo(f"installed {installed_shell} completion at {target_path}")


def _load_secret_store(config: Path) -> SecretStore:
    """Load config and return a SecretStore instance."""

    runtime = load_config(config)
    secrets_dir = runtime.repo_dir / "data/private/secrets"
    return SecretStore(secrets_dir)


@secrets_app.command("add")
def secrets_add(
    value: str = typer.Argument(..., help="Literal secret value to store."),
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
) -> None:
    """Add one literal secret to the store."""

    store = _load_secret_store(config)
    if store.add(value):
        typer.echo(f"added secret: {hash_bytes(value.encode('utf-8'))[:12]}")
    else:
        typer.echo("secret already present")


@secrets_app.command("remove")
def secrets_remove(
    value: str = typer.Argument(
        ..., help="Literal secret value or hash prefix to remove."
    ),
    by_hash: bool = typer.Option(
        False, "--by-hash", help="Interpret VALUE as a hash prefix."
    ),
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
) -> None:
    """Remove a secret from the store."""

    store = _load_secret_store(config)
    removed = store.remove_by_hash(value) if by_hash else store.remove(value)
    if removed:
        typer.echo("removed")
    else:
        typer.echo("not found", err=True)
        raise typer.Exit(code=1)


@secrets_app.command("list")
def secrets_list(
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
) -> None:
    """List stored secrets (values masked)."""

    store = _load_secret_store(config)
    entries = store.list_secrets()
    if not entries:
        typer.echo("no secrets stored")
        return
    typer.echo(f"{'hash':<16} {'value':<24} count={len(entries)}")
    typer.echo("-" * 40)
    for h, masked, _raw in entries:
        typer.echo(f"{h:<16} {masked:<24}")


@secrets_app.command("hash")
def secrets_hash(
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
) -> None:
    """Print the deterministic hash of all stored secrets."""

    store = _load_secret_store(config)
    typer.echo(store.compute_hash())


@secrets_app.command("scan-env")
def secrets_scan_env(
    env_file: Path = typer.Argument(
        ..., help="Path to .env file to scan.", exists=True
    ),
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
) -> None:
    """Scan a .env file for sensitive variables and add their values."""

    store = _load_secret_store(config)
    added = store.scan_and_record(env_file)
    typer.echo(f"scan complete: added={added} from {env_file}")


def main() -> None:
    """Run the Typer application."""

    app()
