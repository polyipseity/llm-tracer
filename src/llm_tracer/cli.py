"""Typer-based CLI for ingest, publish, decision logging, and syncing."""

from pathlib import Path

import typer

from llm_tracer.adapters import ADAPTERS
from llm_tracer.core.bootstrap import bootstrap_traces_repo
from llm_tracer.core.config import load_config
from llm_tracer.core.decisions import record_decision
from llm_tracer.core.engine import publish_sanitized
from llm_tracer.core.git_sync import sync_public_repo
from llm_tracer.core.hf_sync import sync_hugging_face
from llm_tracer.core.ingest import ingest_source

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
    config: Path = typer.Option(..., help="Path to llm-tracer.toml"),
) -> None:
    """Ingest one source into private partitioned storage."""

    runtime = load_config(config)
    inserted = ingest_source(source, runtime)
    typer.echo(f"ingest complete: inserted={inserted} source={source}")


@app.command("publish")
def publish(
    config: Path = typer.Option(..., help="Path to llm-tracer.toml"),
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
    config: Path = typer.Option(..., help="Path to llm-tracer.toml"),
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


@app.command("sync-hf")
def sync_hf(config: Path = typer.Option(..., help="Path to llm-tracer.toml")) -> None:
    """Sync sanitized public partitions to Hugging Face dataset repo."""

    runtime = load_config(config)
    uploads = sync_hugging_face(runtime)
    typer.echo(f"huggingface sync complete: uploads={uploads}")


def main() -> None:
    """Run the Typer application."""

    app()
