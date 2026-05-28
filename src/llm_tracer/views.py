"""Symlink-based private chat views grouped by normalized tag hierarchy."""

import os
import shutil
from pathlib import Path

from llm_tracer.config import TracerConfig
from llm_tracer.storage import ensure_dir, private_chat_path, read_private_chats

"""Public symbols exported by this module."""
__all__ = ("rebuild_private_tag_views",)


"""Relative location of private chat view roots under the configured repo."""
_PRIVATE_VIEWS_ROOT = Path("data/private/views")


"""Tag-hierarchy directory inside the private views root."""
_BY_TAG_DIRNAME = "by_tag"


"""Temporary directory name used for atomic tag-view rebuilds."""
_TEMP_BY_TAG_DIRNAME = ".tmp-by_tag"


def _tag_path_components(tag: str) -> tuple[str, ...]:
    """Return filesystem path components representing one normalized tag."""

    return tuple(part for part in tag.split("/") if part)


def _relative_symlink_target(*, source_path: Path, link_dir: Path) -> Path:
    """Build a relative symlink target path from one link directory to source."""

    target = Path(os.path.relpath(source_path, start=link_dir))
    if target.is_absolute():
        raise ValueError("private tag view symlink targets must be relative")
    return target


def rebuild_private_tag_views(config: TracerConfig) -> int:
    """Rebuild private symlink views by tag hierarchy and return symlink count."""

    private_chats_dir = config.repo_dir / "data/private/chats"
    views_root = config.repo_dir / _PRIVATE_VIEWS_ROOT
    by_tag_root = views_root / _BY_TAG_DIRNAME
    temp_root = views_root / _TEMP_BY_TAG_DIRNAME

    if temp_root.exists():
        shutil.rmtree(temp_root)
    ensure_dir(temp_root)

    sessions = read_private_chats(private_chats_dir)
    links_written = 0
    for session in sorted(sessions.values(), key=lambda item: item.id):
        source_path = private_chat_path(private_chats_dir, session)
        if not source_path.exists():
            continue
        for tag in session.tags:
            tag_dir = temp_root.joinpath(*_tag_path_components(tag))
            ensure_dir(tag_dir)
            link_path = tag_dir / f"{session.id}.json"
            relative_target = _relative_symlink_target(
                source_path=source_path,
                link_dir=tag_dir,
            )
            if link_path.exists() or link_path.is_symlink():
                link_path.unlink(missing_ok=True)
            link_path.symlink_to(relative_target)
            links_written += 1

    if by_tag_root.exists():
        shutil.rmtree(by_tag_root)
    temp_root.rename(by_tag_root)

    return links_written
