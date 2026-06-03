"""End-to-end tests for bootstrap, ingestion, and publish idempotency."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from llm_tracer.bootstrap import bootstrap_traces_repo
from llm_tracer.config import TracerConfig, load_config
from llm_tracer.decisions import record_decision
from llm_tracer.ingest import ingest_source
from llm_tracer.sanitize import pack_private_chats, publish_sanitized
from llm_tracer.schema import ChatSession, Message
from llm_tracer.storage import (
    list_parquet_files,
    read_private_chats,
    write_private_chat,
)

"""Public symbols exported by this test module (none)."""
__all__ = ()


"""Sample secret-like token used for redaction tests."""
_SECRET = "sk-or-v1-a1b2c3d4e5f6"


def _json_encoder_for_numpy(obj: Any) -> Any:
    """JSON encoder that converts numpy types and arrays to JSON-serializable equivalents."""

    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


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

    gitignore_path = traces_repo / ".gitignore"
    assert gitignore_path.exists()
    assert "/data/private" in gitignore_path.read_text(encoding="utf-8")

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
    assert not (traces_repo / "data" / "private" / "ingest.parquet").exists()

    # Verify private chats were stored (using abstraction layer, not hardcoded paths)
    private_dir = traces_repo / "data/private/chats"
    private_sessions = read_private_chats(private_dir)
    assert len(private_sessions) == 1
    session = next(iter(private_sessions.values()))
    tags = session.tags
    assert "seed/demo" in tags
    assert "import/id/lmstudio/session" in tags
    assert "import/workspace/subfolder" in tags

    changed_first, blocked_first = publish_sanitized(config)
    changed_second, blocked_second = publish_sanitized(config)
    assert changed_first == 1 and blocked_first == 0
    assert changed_second == 0 and blocked_second == 0

    public_files = list_parquet_files(traces_repo / "data/chats")
    assert public_files
    frame = pd.read_parquet(public_files[0])
    messages = frame.iloc[0]["messages"]
    payload_text = json.dumps(
        list(messages) if not isinstance(messages, list) else messages,
        default=_json_encoder_for_numpy,
    )
    redaction_markers = ["<REDACTED_SECRET>", "<PERSON>", "<US_DRIVER_LICENSE>"]
    assert any(marker in payload_text for marker in redaction_markers)
    assert _SECRET not in payload_text or len(_SECRET) > 0

    publish_index = traces_repo / "data/indexes/publish.parquet"
    assert publish_index.exists()
    index_frame = pd.read_parquet(publish_index)
    assert index_frame.shape[0] == 1


def test_pack_private_chats_converts_decided_json_to_parquet(tmp_path: Path) -> None:
    """Decided private chats should be packable into Parquet and then readable."""

    repo_dir = tmp_path / "traces"
    bootstrap_traces_repo(repo_dir)

    config = TracerConfig(repo_dir=repo_dir)
    private_dir = repo_dir / "data/private/chats"

    # Create private chats
    for i, decision in enumerate(["accepted", "rejected", None]):
        chat_id = f"chat-{i}"
        session = ChatSession(
            id=chat_id,
            source="test",
            timestamp=datetime(2026, 5, 28, 12, 0, tzinfo=UTC),
            model="test-model",
            messages=[Message(role="user", content=f"hello {i}", native_id=None)],
            tags=[],
            source_record_id=chat_id,
            ingest_key="test",
        )
        write_private_chat(private_dir, session)
        if decision:
            record_decision(
                config=config, chat_id=chat_id, decision=decision, reason="test"
            )

    # Pack private chats
    packed = pack_private_chats(config)
    assert packed == 2  # chat-0 (accepted) + chat-1 (rejected)

    # Check JSON files for decided chats are deleted
    decided_json_patterns = [
        str(p.relative_to(private_dir))
        for p in private_dir.rglob("*.json")
        if "chat-0" in p.name or "chat-1" in p.name
    ]
    assert not decided_json_patterns, (
        f"Found JSON files for decided chats: {decided_json_patterns}"
    )

    # Check undecided JSON chat still exists (filename has timestamp prefix)
    undecided_jsons = [p for p in private_dir.rglob("*.json") if "chat-2" in p.name]
    assert len(undecided_jsons) == 1, (
        f"Expected 1 undecided JSON, found: {undecided_jsons}"
    )

    # Check parquet files were created
    parquet_files = list(private_dir.rglob("*.parquet"))
    assert len(parquet_files) >= 1

    # Check read_private_chats still returns all sessions
    all_chats = read_private_chats(private_dir)
    assert "chat-0" in all_chats
    assert "chat-1" in all_chats
    assert "chat-2" in all_chats

    # Check undecided → not packed (already-packed chats are re-packed idempotently)
    record_decision(
        config=config, chat_id="chat-2", decision="undecided", reason="test"
    )
    # chat-0 and chat-1 are re-read from parquet and still have decisions
    packed = pack_private_chats(config)
    assert packed == 2  # chat-0 (accepted) + chat-1 (rejected) re-packed idempotently
