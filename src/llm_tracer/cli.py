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
from llm_tracer.sanitize import publish_sanitized
from llm_tracer.sync import sync_all
from llm_tracer.sync.git import sync_public_repo
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

app.add_typer(completion_app, name="completion")

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
    updated = _REPO_DIR_PATTERN.sub(repo_dir_line, existing, count=1)
    if updated == existing:
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
    source: str = typer.Option(
        ..., help=f"Ingest source slug. One of: {', '.join(ADAPTERS)}"
    ),
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
) -> None:
    """Ingest one source into private partitioned storage."""

    runtime = load_config(config)
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
    changed = publish_sanitized(runtime)
    typer.echo(f"publish complete: changed={changed}")
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


@app.command("purge-ingested")
def purge_ingested(
    source: str = typer.Option(
        ..., help=f"Source slug to purge. One of: {', '.join(ADAPTERS)}"
    ),
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
) -> None:
    """Delete all privately-stored sessions that were ingested from the given source."""

    runtime = load_config(config)
    deleted = purge_ingested_source(source, runtime)
    typer.echo(f"purge complete: deleted={deleted} source={source}")
    links = rebuild_private_tag_views(runtime)
    typer.echo(f"private tag views rebuilt: links={links}")


@app.command("rebuild-private-views")
def rebuild_private_views_command(
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
) -> None:
    """Rebuild symlink views for private chats grouped by tag hierarchy."""

    runtime = load_config(config)
    links = rebuild_private_tag_views(runtime)
    typer.echo(f"private tag views rebuilt: links={links}")


@app.command("reprocess")
def reprocess_command(
    config: Path = typer.Option(_DEFAULT_CONFIG_NAME, help="Path to llm-tracer.toml"),
    attachment_policy: str | None = typer.Option(
        None,
        help=f"Attachment policy to apply. One of: {', '.join(p.value for p in AttachmentPolicy)}",
    ),
) -> None:
    """Transform private chat data based on attachment policy."""

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
        msg = f"reprocess complete: processed={processed}"
        if errors:
            msg += f" errors={errors}"
        typer.echo(msg)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error


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


def main() -> None:
    """Run the Typer application."""

    app()
