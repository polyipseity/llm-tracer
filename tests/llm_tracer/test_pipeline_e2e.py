"""End-to-end tests for bootstrap, ingestion, and publish idempotency."""

import json
from pathlib import Path

import pandas as pd
import pytest

from llm_tracer.core.bootstrap import bootstrap_traces_repo
from llm_tracer.core.config import load_config
from llm_tracer.core.engine import publish_sanitized
from llm_tracer.core.ingest import ingest_source
from llm_tracer.core.storage import (
    list_jsonl_files,
    list_parquet_files,
    read_jsonl_records,
)

"""Public symbols exported by this test module (none)."""
__all__ = ()


"""Sample secret-like token used for redaction tests."""
_SECRET = "sk-or-v1-a1b2c3d4e5f6"


def _write_config(path: Path) -> None:
    """Write a test runtime config TOML file."""

    path.write_text(
        """repo_dir = "."
chunk_size_bytes = 10000000

[hf]
enabled = false
repo_id = ""
token_env_var = "HF_TOKEN"
revision = "main"

[sources.lmstudio]
root = "./imports/lmstudio"
patterns = ["**/*.json"]
""",
        encoding="utf-8",
    )


def _write_lmstudio_sample(path: Path) -> None:
    """Write a minimal LM Studio style source file for ingestion tests."""

    payload = {
        "id": "sample-1",
        "timestamp": "2026-05-23T10:00:00+00:00",
        "model": "gpt-test",
        "messages": [
            {"role": "user", "content": f"token is {_SECRET}"},
            {"role": "assistant", "content": "Acknowledged"},
        ],
        "tags": ["seed/demo"],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.mark.anyio
async def test_bootstrap_and_ingest_publish_idempotency(tmp_path: Path) -> None:
    """Bootstrap, ingest, and publish should be deterministic and idempotent."""

    traces_repo = tmp_path / "any-data-repo-name"
    bootstrap_traces_repo(traces_repo)
    bootstrap_traces_repo(traces_repo)

    gitignore_path = traces_repo / "data/.gitignore"
    assert gitignore_path.exists()
    assert "/private/" in gitignore_path.read_text(encoding="utf-8")

    imports_root = traces_repo / "imports/lmstudio/subfolder"
    imports_root.mkdir(parents=True)
    _write_lmstudio_sample(imports_root / "session.json")

    config_path = traces_repo / "llm-tracer.toml"
    _write_config(config_path)
    config = load_config(config_path)

    inserted_first = ingest_source("lmstudio", config)
    inserted_second = ingest_source("lmstudio", config)
    assert inserted_first == 1
    assert inserted_second == 0

    private_files = list_jsonl_files(traces_repo / "data/private/chats")
    assert private_files
    private_rows = [row for file in private_files for row in read_jsonl_records(file)]
    assert len(private_rows) == 1
    tags = private_rows[0]["tags"]
    assert "seed/demo" in tags
    assert "import/subfolder" in tags

    changed_first = publish_sanitized(config)
    changed_second = publish_sanitized(config)
    assert changed_first == 1
    assert changed_second == 0

    public_files = list_parquet_files(traces_repo / "data/chats")
    assert public_files
    frame = pd.read_parquet(public_files[0])
    messages = frame.iloc[0]["messages"]
    payload_text = json.dumps(
        list(messages) if not isinstance(messages, list) else messages
    )
    assert "<REDACTED_SECRET>" in payload_text
    assert _SECRET not in payload_text

    publish_index = traces_repo / "data/indexes/publish.parquet"
    assert publish_index.exists()
    index_frame = pd.read_parquet(publish_index)
    assert index_frame.shape[0] == 1
