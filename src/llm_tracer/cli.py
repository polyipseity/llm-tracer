"""Typer-based CLI for ingest, publish, decision logging, and syncing."""

from pathlib import Path

import typer

from llm_tracer.adapters import ADAPTERS
from llm_tracer.bootstrap import bootstrap_traces_repo
from llm_tracer.config import load_config
from llm_tracer.decisions import record_decision
from llm_tracer.ingest import ingest_source, purge_ingested_source
from llm_tracer.sanitize import publish_sanitized
from llm_tracer.sync.git import sync_public_repo
from llm_tracer.sync.hugging_face import sync_hugging_face

"""Public symbols exported by this module."""
__all__ = ("app", "main")


"""Root Typer application instance."""
app = typer.Typer(help="Decoupled LLM trace ingestion and publish pipeline.")


@app.command("init-traces-repo")
def init_traces_repo(repo_dir: Path) -> None:
    """Create or validate traces repository structure idempotently."""

    bootstrap_traces_repo(repo_dir)
    typer.echo(f"initialized traces repo layout at {repo_dir}")


@app.command("ingest")
def ingest(
    source: str = typer.Option(
        ..., help=f"Ingest source slug. One of: {', '.join(ADAPTERS)}"
    ),
    config: Path = typer.Option("llm-tracer.toml", help="Path to llm-tracer.toml"),
) -> None:
    """Ingest one source into private partitioned storage."""

    runtime = load_config(config)
    inserted = ingest_source(source, runtime)
    typer.echo(f"ingest complete: inserted={inserted} source={source}")


@app.command("publish")
def publish(
    config: Path = typer.Option("llm-tracer.toml", help="Path to llm-tracer.toml"),
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
    config: Path = typer.Option("llm-tracer.toml", help="Path to llm-tracer.toml"),
    chat_id: str = typer.Option(..., help="Chat identifier to annotate"),
    decision: str = typer.Option(..., help="Decision value: accepted|rejected"),
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


@app.command("sync-hugging-face")
def sync_hugging_face_command(
    config: Path = typer.Option("llm-tracer.toml", help="Path to llm-tracer.toml"),
) -> None:
    """Sync sanitized public partitions to Hugging Face dataset repo."""

    runtime = load_config(config)
    uploads = sync_hugging_face(runtime)
    typer.echo(f"Hugging Face sync complete: uploads={uploads}")


@app.command("purge-ingested")
def purge_ingested(
    source: str = typer.Option(
        ..., help=f"Source slug to purge. One of: {', '.join(ADAPTERS)}"
    ),
    config: Path = typer.Option("llm-tracer.toml", help="Path to llm-tracer.toml"),
) -> None:
    """Delete all privately-stored sessions that were ingested from the given source."""

    runtime = load_config(config)
    deleted = purge_ingested_source(source, runtime)
    typer.echo(f"purge complete: deleted={deleted} source={source}")


def main() -> None:
    """Run the Typer application."""

    app()
