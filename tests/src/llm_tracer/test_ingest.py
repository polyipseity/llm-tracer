"""Unit tests for `llm_tracer.ingest`."""

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from llm_tracer.bootstrap import bootstrap_traces_repo
from llm_tracer.config import SourceConfig, TracerConfig
from llm_tracer.ingest import ingest_source, purge_ingested_source
from llm_tracer.schema import ChatSession, Message
from llm_tracer.storage import read_private_chats, write_private_chat

"""Public symbols exported by this test module (none)."""
__all__ = ()


"""Repository root used for fixture resolution in ingestion tests."""
_REPO_ROOT = Path(__file__).resolve().parents[3]

"""Fixture root shared by adapter ingestion tests."""
_FIXTURES_ROOT = _REPO_ROOT / "examples" / "fixtures"


"""Per-adapter fixture roots/patterns and optional mtime target for deterministic ingestion."""
_ADAPTER_CASES: tuple[tuple[str, Path, list[str], Path | None], ...] = (
    (
        "claude_code",
        _FIXTURES_ROOT / "claude_code" / "projects",
        ["**/*.jsonl"],
        None,
    ),
    (
        "codex",
        _FIXTURES_ROOT / "codex" / "sessions",
        ["**/*.jsonl"],
        None,
    ),
    (
        "lmstudio",
        _FIXTURES_ROOT / "lmstudio" / "conversations",
        ["**/*.json", "**/*.jsonl"],
        None,
    ),
    (
        "local",
        _FIXTURES_ROOT / "local" / "workspaceStorage",
        ["**/*.json", "**/*.jsonl"],
        None,
    ),
    (
        "ollama",
        _FIXTURES_ROOT / "ollama",
        ["**/*"],
        _FIXTURES_ROOT / "ollama" / "history",
    ),
    (
        "opencode",
        _FIXTURES_ROOT / "opencode" / "storage",
        ["**/*.json", "**/*.jsonl"],
        None,
    ),
    (
        "oterm",
        _FIXTURES_ROOT / "oterm",
        ["**/*.db"],
        _FIXTURES_ROOT / "oterm" / "store.db",
    ),
    (
        "pi_coding_agent",
        _FIXTURES_ROOT / "pi_coding_agent" / "sessions",
        ["**/*.json", "**/*.jsonl"],
        None,
    ),
    (
        "vscode",
        _FIXTURES_ROOT / "vscode" / "workspaceStorage",
        ["**/*.json", "**/*.jsonl"],
        None,
    ),
)


def _build_single_source_config(
    *,
    repo_dir: Path,
    source: str,
    root: Path,
    patterns: list[str],
) -> TracerConfig:
    """Build a minimal in-memory config for one source under test."""

    return TracerConfig(
        repo_dir=repo_dir,
        sources={
            source: SourceConfig(
                roots=[root],
                patterns=patterns,
                options={},
            )
        },
    )


@pytest.mark.parametrize(
    ("source", "fixture_root", "patterns", "mtime_target"),
    _ADAPTER_CASES,
)
def test_ingest_source_is_idempotent_for_all_adapters(
    tmp_path: Path,
    source: str,
    fixture_root: Path,
    patterns: list[str],
    mtime_target: Path | None,
) -> None:
    """Every adapter should ingest once and then report zero new inserts."""

    traces_repo = tmp_path / "traces"
    bootstrap_traces_repo(traces_repo)
    config = _build_single_source_config(
        repo_dir=traces_repo,
        source=source,
        root=fixture_root,
        patterns=patterns,
    )

    if mtime_target is not None:
        os.utime(mtime_target, (0, 0))

    stats_first = ingest_source(source, config)
    stats_second = ingest_source(source, config)

    assert stats_first.newly_inserted > 0, (
        f"expected at least one inserted session for {source}"
    )
    assert stats_second.newly_inserted == 0, (
        f"second ingest should be idempotent for {source}"
    )
    assert not (traces_repo / "data" / "private" / "ingest.parquet").exists(), (
        "ingest tracking should be embedded in private chat JSON files"
    )


@pytest.mark.parametrize(
    ("source", "fixture_root", "patterns", "mtime_target"),
    _ADAPTER_CASES,
)
def test_purge_ingested_source_works_for_all_adapters(
    tmp_path: Path,
    source: str,
    fixture_root: Path,
    patterns: list[str],
    mtime_target: Path | None,
) -> None:
    """Every adapter should support purge-ingested and idempotent second purge."""

    traces_repo = tmp_path / "traces"
    bootstrap_traces_repo(traces_repo)
    config = _build_single_source_config(
        repo_dir=traces_repo,
        source=source,
        root=fixture_root,
        patterns=patterns,
    )

    if mtime_target is not None:
        os.utime(mtime_target, (0, 0))

    stats = ingest_source(source, config)
    deleted_first = purge_ingested_source(source, config)
    deleted_second = purge_ingested_source(source, config)

    total_inserted = stats.newly_inserted + stats.already_ingested + stats.updated
    assert total_inserted > 0, f"expected at least one inserted session for {source}"
    if source == "local":
        assert deleted_first == 0, (
            "purge-ingested for local should not delete delegated-source sessions"
        )
    else:
        assert deleted_first == total_inserted, (
            f"purge-ingested should delete exactly the ingested sessions for {source}"
        )
    assert deleted_second == 0, f"second purge should be idempotent for {source}"

    private_sessions = read_private_chats(traces_repo / "data" / "private" / "chats")
    if source == "local":
        assert len(private_sessions) == total_inserted
    else:
        assert not private_sessions, (
            f"private storage should be empty after purge for {source}"
        )
    assert not (traces_repo / "data" / "private" / "ingest.parquet").exists(), (
        "purge should not maintain a separate ingest parquet index"
    )


def test_purge_ingested_source_preserves_manual_sessions(tmp_path: Path) -> None:
    """`purge_ingested_source` should keep manually-authored chats."""

    source = "lmstudio"
    traces_repo = tmp_path / "traces"
    bootstrap_traces_repo(traces_repo)
    config = _build_single_source_config(
        repo_dir=traces_repo,
        source=source,
        root=_FIXTURES_ROOT / "lmstudio" / "conversations",
        patterns=["**/*.json", "**/*.jsonl"],
    )

    stats = ingest_source(source, config)
    assert stats.newly_inserted > 0

    manual_chat = ChatSession(
        id="manual-chat-lmstudio-1",
        source="lmstudio",
        timestamp=datetime(2026, 5, 28, tzinfo=UTC),
        model="manual-model",
        messages=[Message(role="user", content="manual note", native_id=None)],
        tags=["manual/test"],
        source_record_id="manual-chat-lmstudio-1",
        ingest_key=None,
    )
    private_chats_dir = traces_repo / "data" / "private" / "chats"
    write_private_chat(private_chats_dir, manual_chat)

    deleted = purge_ingested_source(source, config)
    assert deleted == stats.newly_inserted

    remaining = read_private_chats(private_chats_dir)
    assert set(remaining.keys()) == {manual_chat.id}
    assert remaining[manual_chat.id].ingest_key is None
