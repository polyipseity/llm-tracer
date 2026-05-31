"""Unit tests for `llm_tracer.bootstrap`."""

from pathlib import Path

from llm_tracer.bootstrap import bootstrap_traces_repo

"""Public symbols exported by this test module (none)."""
__all__ = ()


def test_bootstrap_traces_repo_creates_repo_layout_without_config(
    tmp_path: Path,
) -> None:
    """Bootstrapping the repo should not place `llm-tracer.toml` inside it."""

    repo_dir = tmp_path / "traces-repo"

    bootstrap_traces_repo(repo_dir)

    assert (repo_dir / "data/private/chats").is_dir()
    assert (repo_dir / ".gitignore").read_text(encoding="utf-8") == "/data/private\n"
    assert not (repo_dir / "llm-tracer.toml").exists()
