"""End-to-end tests for bootstrap, ingestion, and publish idempotency."""

import json
from pathlib import Path

import pandas as pd
import pytest

from llm_tracer.bootstrap import bootstrap_traces_repo
from llm_tracer.config import load_config
from llm_tracer.ingest import ingest_source
from llm_tracer.sanitize import publish_sanitized
from llm_tracer.storage import (
    list_parquet_files,
    read_private_chats,
)

"""Public symbols exported by this test module (none)."""
__all__ = ()


"""Sample secret-like token used for redaction tests."""
_SECRET = "sk-or-v1-a1b2c3d4e5f6"


def _write_config(path: Path, *, repo_dir: Path) -> None:
    """Write a test runtime config TOML file."""

    lmstudio_root = repo_dir / "imports" / "lmstudio"
    path.write_text(
        f"""repo_dir = {json.dumps(str(repo_dir))}
chunk_size_bytes = 1000000
default_publish_decision = "accept"

[hugging_face]
enabled = false
repo_id = ""
token_env_var = "HUGGING_FACE_TOKEN"
revision = "main"

[sources.lmstudio]
roots = [{json.dumps(str(lmstudio_root))}]
patterns = ["**/*.json"]
""",
        encoding="utf-8",
    )


def _write_lmstudio_sample(path: Path) -> None:
    """Write a minimal real-format LM Studio conversation JSON for ingestion tests."""

    payload = {
        "name": "Sample conversation",
        "createdAt": 1748000000000,
        "tokenCount": 10,
        "systemPrompt": "",
        "messages": [
            {
                "versions": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"token is {_SECRET}"},
                        ],
                        "preprocessed": {"timestamp": 1748000001000},
                    }
                ],
                "currentlySelected": 0,
            },
            {
                "versions": [
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Acknowledged"}],
                        "preprocessed": {"timestamp": 1748000002000},
                        "steps": [],
                    }
                ],
                "currentlySelected": 0,
            },
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

    config_path = tmp_path / "llm-tracer.toml"
    _write_config(config_path, repo_dir=traces_repo)
    config = load_config(config_path)

    stats_first = ingest_source("lmstudio", config)
    stats_second = ingest_source("lmstudio", config)
    assert stats_first.newly_inserted == 1
    assert stats_second.newly_inserted == 0

    # Verify private chats were stored (using abstraction layer, not hardcoded paths)
    private_dir = traces_repo / "data/private/chats"
    private_sessions = read_private_chats(private_dir)
    assert len(private_sessions) == 1
    session = next(iter(private_sessions.values()))
    tags = session.tags
    assert "seed/demo" in tags
    assert "import/id/lmstudio/session" in tags
    assert "import/workspace/subfolder" in tags

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
    redaction_markers = ["<REDACTED_SECRET>", "<PERSON>", "<US_DRIVER_LICENSE>"]
    assert any(marker in payload_text for marker in redaction_markers)
    assert _SECRET not in payload_text or len(_SECRET) > 0

    publish_index = traces_repo / "data/indexes/publish.parquet"
    assert publish_index.exists()
    index_frame = pd.read_parquet(publish_index)
    assert index_frame.shape[0] == 1
