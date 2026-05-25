"""Ingestion orchestration for adapter normalization into private storage."""

from pathlib import Path

import pandas as pd

from llm_tracer.adapters import get_adapter
from llm_tracer.core.config import TracerConfig
from llm_tracer.core.schema import ChatSession, Message
from llm_tracer.core.tags import normalize_tags
from llm_tracer.storage import (
    read_parquet_dataframe,
    read_partitioned_private_chats,
    write_index_dataframe,
    write_partitioned_jsonl,
)

"""Public symbols exported by this module."""
__all__ = (
    "ingest_source",
    "purge_imported_source",
)


def _merge_session(existing: ChatSession, incoming: ChatSession) -> ChatSession:
    """Merge idempotent upsert fields for an existing chat session.

    Merges tags and appends only new messages (those not already present
    by native_id or by exact role+content match).
    """
    merged_tags = normalize_tags([*existing.tags, *incoming.tags])
    existing_native_ids: set[str] = {
        m.native_id for m in existing.messages if m.native_id is not None
    }
    existing_content: set[tuple[str, str]] = {
        (m.role, m.content) for m in existing.messages
    }
    new_messages: list[Message] = [
        msg
        for msg in incoming.messages
        if (msg.native_id is None or msg.native_id not in existing_native_ids)
        and (msg.role, msg.content) not in existing_content
    ]
    return existing.model_copy(
        update={
            "tags": merged_tags,
            "messages": [*existing.messages, *new_messages],
        }
    )


def _to_record(session: ChatSession) -> dict[str, object]:
    """Serialize a chat session into a JSON-serializable mapping."""

    return session.model_dump(mode="json")


def _private_paths(repo_dir: Path) -> tuple[Path, Path]:
    """Return private chats and private ingest index paths."""

    return (repo_dir / "data/private/chats", repo_dir / "data/private/ingest.parquet")


def ingest_source(source: str, config: TracerConfig) -> int:
    """Ingest one configured source into private partitioned JSONL storage.

    Returns the number of newly inserted chat records.
    """

    if source not in config.sources:
        raise ValueError(f"source {source!r} is not configured in llm-tracer.toml")
    source_config = config.sources[source]
    adapter = get_adapter(source)
    private_chats_dir, ingest_index_path = _private_paths(config.repo_dir)

    existing_sessions = read_partitioned_private_chats(private_chats_dir)
    ingest_df = read_parquet_dataframe(ingest_index_path)
    existing_ingest_keys = (
        set(ingest_df["ingest_key"].tolist())
        if not ingest_df.empty and "ingest_key" in ingest_df
        else set()
    )

    incoming_sessions = adapter.ingest_with_options(
        root=source_config.root,
        patterns=source_config.patterns,
        options=source_config.options,
    )
    inserted = 0
    ingest_rows: list[dict[str, object]] = []
    for session in incoming_sessions:
        ingest_key = session.ingest_key
        if ingest_key is not None and ingest_key in existing_ingest_keys:
            if session.id in existing_sessions:
                existing_sessions[session.id] = _merge_session(
                    existing_sessions[session.id],
                    session,
                )
            else:
                # ingest_key known but session absent from storage (e.g., partial data loss)
                existing_sessions[session.id] = session
                inserted += 1
            continue
        if session.id in existing_sessions:
            existing_sessions[session.id] = _merge_session(
                existing_sessions[session.id], session
            )
        else:
            existing_sessions[session.id] = session
            inserted += 1
        if ingest_key is not None:
            existing_ingest_keys.add(ingest_key)
            ingest_rows.append({"chat_id": session.id, "ingest_key": ingest_key})

    if incoming_sessions:
        rows = [_to_record(session) for session in existing_sessions.values()]
        rows.sort(key=lambda row: (str(row["timestamp"]), str(row["id"])))
        write_partitioned_jsonl(
            private_chats_dir,
            rows,
            max_bytes=config.chunk_size_bytes,
        )

    if ingest_rows:
        appended = pd.concat(
            [ingest_df, pd.DataFrame(ingest_rows)],
            ignore_index=True,
        )
        deduped = appended.drop_duplicates(subset=["ingest_key"], keep="last")
        write_index_dataframe(ingest_index_path, deduped)

    return inserted


def purge_imported_source(source: str, config: TracerConfig) -> int:
    """Delete all privately-stored sessions that were imported from the given source.

    Only sessions whose chat id appears in the ingest index are removed, so
    manually created sessions are left untouched.  Both the partitioned JSONL
    files and the ingest index are rewritten atomically.

    Returns the number of deleted sessions.
    """
    if source not in config.sources:
        raise ValueError(f"source {source!r} is not configured in llm-tracer.toml")
    private_chats_dir, ingest_index_path = _private_paths(config.repo_dir)

    existing_sessions = read_partitioned_private_chats(private_chats_dir)
    ingest_df = read_parquet_dataframe(ingest_index_path)

    if ingest_df.empty or "chat_id" not in ingest_df.columns:
        return 0
    ingest_chat_ids = set(ingest_df["chat_id"].tolist())

    to_delete = {
        sid
        for sid, session in existing_sessions.items()
        if session.source == source and sid in ingest_chat_ids
    }
    if not to_delete:
        return 0

    kept_sessions = {
        sid: s for sid, s in existing_sessions.items() if sid not in to_delete
    }
    rows = [_to_record(s) for s in kept_sessions.values()]
    rows.sort(key=lambda row: (str(row["timestamp"]), str(row["id"])))
    write_partitioned_jsonl(private_chats_dir, rows, max_bytes=config.chunk_size_bytes)

    cleaned_df = ingest_df[~ingest_df["chat_id"].isin(to_delete)]
    write_index_dataframe(ingest_index_path, cleaned_df)

    return len(to_delete)
