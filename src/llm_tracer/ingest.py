"""Ingestion orchestration for adapter normalization into private storage."""

from llm_tracer.adapters import get_adapter
from llm_tracer.config import TracerConfig
from llm_tracer.sanitize import PatternRegistry, Scrubber, sanitize_session
from llm_tracer.sanitize.secrets import SecretStore
from llm_tracer.schema import ChatSession, IngestStats, Message
from llm_tracer.storage import (
    delete_private_chat,
    read_private_chats,
    write_private_chat,
)
from llm_tracer.utils.tags import normalize_tags

"""Public symbols exported by this module."""
__all__ = (
    "ingest_source",
    "purge_ingested_source",
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


def ingest_source(source: str, config: TracerConfig) -> IngestStats:
    """Ingest one configured source into private partitioned JSONL storage.

    Returns detailed ingestion statistics: newly_inserted, already_ingested, updated, errors.
    """

    if source not in config.sources:
        raise ValueError(f"source {source!r} is not configured in llm-tracer.toml")
    source_config = config.sources[source]
    adapter = get_adapter(source)
    private_chats_dir = config.repo_dir / "data/private/chats"

    existing_sessions = read_private_chats(private_chats_dir)
    existing_ingest_keys = {
        session.ingest_key
        for session in existing_sessions.values()
        if session.ingest_key is not None
    }

    incoming_sessions = adapter.ingest_with_options(
        roots=source_config.roots,
        patterns=source_config.patterns,
        options=source_config.options,
    )
    newly_inserted = 0
    already_ingested = 0
    updated = 0
    updated_ids: set[str] = set()
    errors: list[dict[str, str]] = []
    for session in incoming_sessions:
        ingest_key = session.ingest_key
        if ingest_key is not None and ingest_key in existing_ingest_keys:
            if session.id in existing_sessions:
                existing_sessions[session.id] = _merge_session(
                    existing_sessions[session.id],
                    session,
                )
                updated += 1
            else:
                # ingest_key known but session absent from storage (e.g., partial data loss)
                existing_sessions[session.id] = session
                newly_inserted += 1
            already_ingested += 1
            updated_ids.add(session.id)
            continue
        if session.id in existing_sessions:
            existing_sessions[session.id] = _merge_session(
                existing_sessions[session.id], session
            )
            updated += 1
        else:
            existing_sessions[session.id] = session
            newly_inserted += 1
        updated_ids.add(session.id)
        if ingest_key is not None:
            existing_ingest_keys.add(ingest_key)

    secret_store = SecretStore(config.repo_dir / "data/private/secrets")
    pattern_registry = PatternRegistry(config.sanitize.to_pattern_config())
    scrubber = Scrubber(secret_store, pattern_registry=pattern_registry)

    for sid in updated_ids:
        session = existing_sessions[sid]
        sanitized = sanitize_session(session, scrubber, phase_b=False)
        write_private_chat(private_chats_dir, sanitized)

    return IngestStats(
        newly_inserted=newly_inserted,
        already_ingested=already_ingested,
        updated=updated,
        errors=errors,
    )


def purge_ingested_source(source: str, config: TracerConfig) -> int:
    """Delete all privately-stored sessions that were ingested from the given source.

    Only sessions with a non-null ingest key are removed, so manually created
    sessions are left untouched.

    Returns the number of deleted sessions.
    """
    if source not in config.sources:
        raise ValueError(f"source {source!r} is not configured in llm-tracer.toml")
    private_chats_dir = config.repo_dir / "data/private/chats"

    existing_sessions = read_private_chats(private_chats_dir)

    to_delete = {
        sid
        for sid, session in existing_sessions.items()
        if session.source == source and session.ingest_key is not None
    }
    if not to_delete:
        return 0

    for sid in to_delete:
        delete_private_chat(private_chats_dir, sid)

    return len(to_delete)
