"""Bootstrap helpers for initializing an external traces data repository."""

from pathlib import Path

from llm_tracer.storage import ensure_dir

"""Public symbols exported by this module."""
__all__ = ("bootstrap_traces_repo",)


"""Default data subdirectories required by the pipeline."""
_REQUIRED_DATA_DIRS = (
    "data/chats",
    "data/decisions",
    "data/indexes",
    "data/private/chats",
)


def _ensure_data_gitignore(path: Path) -> None:
    """Ensure `data/.gitignore` exists and ignores the private subtree."""

    if path.exists():
        content = path.read_text(encoding="utf-8")
        if "/private/" in {line.strip() for line in content.splitlines()}:
            return
        trimmed = content.rstrip("\n")
        new_content = f"{trimmed}\n/private/\n" if trimmed else "/private/\n"
        path.write_text(new_content, encoding="utf-8")
        return
    path.write_text("/private/\n", encoding="utf-8")


def bootstrap_traces_repo(repo_dir: Path) -> None:
    """Create or validate required traces repository structure idempotently."""

    ensure_dir(repo_dir)
    for rel in _REQUIRED_DATA_DIRS:
        ensure_dir(repo_dir / rel)
    _ensure_data_gitignore(repo_dir / "data/.gitignore")
