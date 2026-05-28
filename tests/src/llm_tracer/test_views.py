"""Unit tests for `llm_tracer.views`."""

import os
from datetime import UTC, datetime
from pathlib import Path

from llm_tracer.bootstrap import bootstrap_traces_repo
from llm_tracer.config import TracerConfig
from llm_tracer.schema import ChatSession, Message
from llm_tracer.storage import private_chat_path, write_private_chat
from llm_tracer.views import rebuild_private_tag_views

"""Public symbols exported by this test module (none)."""
__all__ = ()


def _chat(*, chat_id: str, timestamp: datetime, tags: list[str]) -> ChatSession:
    """Build a minimal chat session fixture for private-view tests."""

    return ChatSession(
        id=chat_id,
        source="vscode",
        timestamp=timestamp,
        model="gpt-test",
        messages=[Message(role="user", content="hello", native_id=None)],
        tags=tags,
        source_record_id=chat_id,
        ingest_key="ingest-test-key",
    )


def test_rebuild_private_tag_views_creates_hierarchy_symlinks(tmp_path: Path) -> None:
    """Rebuilding views should create symlinks under tag hierarchy folders."""

    repo_dir = tmp_path / "traces"
    bootstrap_traces_repo(repo_dir)
    config = TracerConfig(repo_dir=repo_dir)

    chats_dir = repo_dir / "data/private/chats"
    first = _chat(
        chat_id="chat-1",
        timestamp=datetime(2026, 5, 28, 12, 0, tzinfo=UTC),
        tags=["import/workspace/llm-tracer", "seed/demo"],
    )
    second = _chat(
        chat_id="chat-2",
        timestamp=datetime(2026, 5, 28, 13, 0, tzinfo=UTC),
        tags=["import/workspace/llm-tracer"],
    )
    write_private_chat(chats_dir, first)
    write_private_chat(chats_dir, second)

    links = rebuild_private_tag_views(config)

    assert links == 3
    by_tag_root = repo_dir / "data/private/views/by_tag"
    workspace_dir = by_tag_root / "import/workspace/llm-tracer"
    seed_dir = by_tag_root / "seed/demo"
    assert workspace_dir.is_dir()
    assert seed_dir.is_dir()

    link_one = workspace_dir / "chat-1.json"
    link_two = workspace_dir / "chat-2.json"
    seed_link = seed_dir / "chat-1.json"
    assert link_one.is_symlink()
    assert link_two.is_symlink()
    assert seed_link.is_symlink()

    assert not Path(os.readlink(link_one)).is_absolute()
    assert not Path(os.readlink(link_two)).is_absolute()
    assert not Path(os.readlink(seed_link)).is_absolute()

    assert link_one.resolve() == private_chat_path(chats_dir, first)
    assert link_two.resolve() == private_chat_path(chats_dir, second)
    assert seed_link.resolve() == private_chat_path(chats_dir, first)


def test_rebuild_private_tag_views_removes_stale_links(tmp_path: Path) -> None:
    """Rebuilding views should atomically replace stale tag-link directories."""

    repo_dir = tmp_path / "traces"
    bootstrap_traces_repo(repo_dir)
    config = TracerConfig(repo_dir=repo_dir)

    chats_dir = repo_dir / "data/private/chats"
    session = _chat(
        chat_id="chat-1",
        timestamp=datetime(2026, 5, 28, 12, 0, tzinfo=UTC),
        tags=["import/workspace/llm-tracer"],
    )
    write_private_chat(chats_dir, session)

    first_links = rebuild_private_tag_views(config)
    assert first_links == 1

    stale_dir = repo_dir / "data/private/views/by_tag/stale"
    stale_dir.mkdir(parents=True)
    stale_file = stale_dir / "old.txt"
    stale_file.write_text("stale", encoding="utf-8")

    second_links = rebuild_private_tag_views(config)
    assert second_links == 1
    assert not stale_file.exists()
