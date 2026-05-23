"""Git repository synchronization helpers for the public data repository."""

from __future__ import annotations

import subprocess
from pathlib import Path

"""Public symbols exported by this module."""
__all__ = ("sync_public_repo",)


def sync_public_repo(
    repo_path: Path,
    commit_message: str,
    *,
    push: bool = False,
    remote: str = "origin",
    branch: str = "main",
) -> bool:
    """Stage and commit pending changes, and optionally push to remote.

    Returns `True` when a commit is created, otherwise `False`.
    """

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    if not status.stdout.strip():
        return False

    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", commit_message], cwd=repo_path, check=True)
    if push:
        subprocess.run(["git", "push", remote, branch], cwd=repo_path, check=True)
    return True
