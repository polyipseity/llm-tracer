"""Unit tests for `llm_tracer.cli`."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from llm_tracer.cli import app

"""Public symbols exported by this test module (none)."""
__all__ = ()


"""CLI runner used for command-level tests."""
_RUNNER = CliRunner()


def test_init_traces_repo_writes_config_in_current_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`init-traces-repo` should place config in cwd, not inside the repo."""

    monkeypatch.chdir(tmp_path)

    result = _RUNNER.invoke(app, ["init-traces-repo", "traces-repo"])

    assert result.exit_code == 0, result.stdout
    config_path = tmp_path / "llm-tracer.toml"
    assert config_path.exists()
    config_text = config_path.read_text(encoding="utf-8")
    assert 'repo_dir = "traces-repo"' in config_text
    assert (tmp_path / "traces-repo" / "data/private/chats").is_dir()
    assert not (tmp_path / "traces-repo" / "llm-tracer.toml").exists()


def test_init_traces_repo_updates_only_repo_dir_in_existing_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`init-traces-repo` should update an existing cwd config in place."""

    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "llm-tracer.toml"
    config_path.write_text(
        """repo_dir = \".\"
chunk_size_bytes = 42

[sources.vscode]
""",
        encoding="utf-8",
    )

    result = _RUNNER.invoke(app, ["init-traces-repo", "nested/traces-repo"])

    assert result.exit_code == 0, result.stdout
    config_text = config_path.read_text(encoding="utf-8")
    assert config_text.startswith('repo_dir = "nested/traces-repo"\n')
    assert "chunk_size_bytes = 42" in config_text
    assert "[sources.vscode]" in config_text
