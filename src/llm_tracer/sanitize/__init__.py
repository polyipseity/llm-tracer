"""Sanitization and publish engine from private JSONL to public Parquet partitions."""

import json
import re
from importlib import import_module
from importlib.util import find_spec
from typing import Any

import pandas as pd

from llm_tracer.config import TracerConfig
from llm_tracer.decisions import read_latest_decisions
from llm_tracer.sanitize.scanner import ScannerConfig, scan_sessions
from llm_tracer.sanitize.secrets import SecretStore
from llm_tracer.schema import ChatSession
from llm_tracer.storage import (
    delete_private_chat,
    list_parquet_files,
    private_chat_path,
    read_parquet_dataframe,
    read_private_chats,
    write_index_dataframe,
    write_partitioned_parquet,
    write_private_chat,
)
from llm_tracer.utils.hashing import compute_content_hash

"""Public symbols exported by this module."""
__all__ = (
    "pack_private_chats",
    "publish_sanitized",
    "sanitize_private",
    "unpack_private_chats",
)


"""Fallback email pattern used when Presidio is unavailable."""
_EMAIL_PATTERN: re.Pattern[str] | None = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)

"""Subdirectory for scan reports under the private data tree."""
_REPORTS_SUBDIR = "data/private/reports"


"""Runtime indicator that Presidio NLP modules are importable."""
_PRESIDIO_AVAILABLE: bool = (
    find_spec("presidio_analyzer") is not None
    and find_spec("presidio_anonymizer") is not None
)


class _Scrubber:
    """Text scrubber that applies Phase A (SecretStore) then Phase B (Presidio/PII)."""

    def __init__(self, secret_store: SecretStore) -> None:
        """Initialize with mandatory SecretStore and optional Presidio."""

        self._secret_store = secret_store
        self._analyzer = None
        self._anonymizer = None
        if _PRESIDIO_AVAILABLE:
            analyzer_module = import_module("presidio_analyzer")
            anonymizer_module = import_module("presidio_anonymizer")
            analyzer_type = getattr(analyzer_module, "AnalyzerEngine")
            anonymizer_type = getattr(anonymizer_module, "AnonymizerEngine")
            self._analyzer = analyzer_type()
            self._anonymizer = anonymizer_type()

    def scrub_text(self, text: str, *, phase_b: bool = True) -> str:
        """Sanitize a text field and return redacted output.

        Phase A: deterministic secret replacement (always applied).
        Phase B: Presidio-based PII redaction (applied only when *phase_b* is True).
        """

        # Phase A — deterministic secret replacement
        text = self._secret_store.replace_all(text)

        # Phase B — PII redaction
        if phase_b:
            if self._analyzer is not None and self._anonymizer is not None:
                results = self._analyzer.analyze(text=text, language="en")
                if results:
                    anonymized = self._anonymizer.anonymize(
                        text=text, analyzer_results=results
                    )
                    text = anonymized.text
            # Email regex fallback when Presidio unavailable
            elif _EMAIL_PATTERN is not None:
                text = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
        return text


def _scrub_tool_call(
    call: dict[str, Any], scrubber: _Scrubber, *, phase_b: bool = True
) -> dict[str, Any]:
    """Recursively scrub all string values within a tool-call dict."""

    result: dict[str, Any] = {}
    for key, value in call.items():
        if isinstance(value, str):
            result[key] = scrubber.scrub_text(value, phase_b=phase_b)
        elif isinstance(value, dict):
            result[key] = _scrub_tool_call(value, scrubber, phase_b=phase_b)
        else:
            result[key] = value
    return result


def _scrub_tag(tag: str, scrubber: _Scrubber, *, phase_b: bool = True) -> str:
    """Scrub PII from the title component of ``import/title/`` tags."""

    prefix = "import/title/"
    if not tag.startswith(prefix):
        return tag
    title = tag[len(prefix) :]
    scrubbed = scrubber.scrub_text(title, phase_b=phase_b)
    normalized = " ".join(scrubbed.strip().split()).replace("/", "_").replace("\\", "_")
    return f"{prefix}{normalized or 'unknown'}"


def _sanitize_session(
    session: ChatSession, scrubber: _Scrubber, *, phase_b: bool = True
) -> ChatSession:
    """Return a sanitized copy of one chat session.

    If *phase_b* is False, only Phase A (deterministic secret replacement) runs.
    """

    sanitized_messages = [
        message.model_copy(
            update={
                "content": scrubber.scrub_text(message.content, phase_b=phase_b),
                "tool_calls": (
                    [
                        _scrub_tool_call(call, scrubber, phase_b=phase_b)
                        for call in message.tool_calls
                    ]
                    if message.tool_calls is not None
                    else None
                ),
            }
        )
        for message in session.messages
    ]
    sanitized_tags = [
        _scrub_tag(tag, scrubber, phase_b=phase_b) for tag in session.tags
    ]
    return session.model_copy(
        update={"messages": sanitized_messages, "tags": sanitized_tags}
    )


def _index_map(frame: pd.DataFrame) -> dict[str, str]:
    """Build `chat_id -> content_hash` mapping from a publish index frame."""

    if frame.empty or "chat_id" not in frame or "content_hash" not in frame:
        return {}
    rows = frame[["chat_id", "content_hash"]].to_dict(orient="records")
    return {str(row["chat_id"]): str(row["content_hash"]) for row in rows}


def _should_publish(
    chat_id: str,
    decision_map: dict[str, str],
    default_publish_decision: str,
) -> bool:
    """Return True if a chat should be included in the published output."""

    decision = decision_map.get(chat_id, "undecided")
    if decision == "accepted":
        return True
    if decision == "rejected":
        return False
    return default_publish_decision == "accept"


def _check_deny_patterns(session: ChatSession, patterns: list[str]) -> bool:
    """Check if *session* matches any deny pattern.

    Returns ``True`` if the session should be *excluded* from public output.
    """

    if not patterns:
        return False
    for message in session.messages:
        for pattern in patterns:
            if re.search(pattern, message.content):
                return True
    return False


def sanitize_private(config: TracerConfig) -> int:
    """Apply Phase A (SecretStore) redaction to all private sessions in-place.

    Returns the number of sessions that changed.
    """

    private_dir = config.repo_dir / "data/private/chats"
    private_sessions = read_private_chats(private_dir)
    secret_store = SecretStore(config.repo_dir / "data/private/secrets")
    scrubber = _Scrubber(secret_store)

    changed = 0
    for chat_id, session in private_sessions.items():
        sanitized = _sanitize_session(session, scrubber, phase_b=False)
        if sanitized != session:
            chat_path = private_chat_path(private_dir, sanitized)
            # Persist updated session as private chat record
            session_data = sanitized.model_dump(mode="json")
            chat_path.write_text(
                json.dumps(session_data, ensure_ascii=False),
                encoding="utf-8",
            )
            changed += 1
    return changed


def publish_sanitized(
    config: TracerConfig,
    *,
    no_scan: bool = False,
) -> tuple[int, int]:
    """Publish sanitized chats from private store into tracked partitioned parquet.

    Phase A (SecretStore) is applied to both private and public copies.
    Phase B (Presidio PII) is applied only to the public copy.
    Scanner gate (detect-secrets) is applied before writing public output.

    Returns ``(changed, blocked)`` where *changed* is the number of
    inserted/updated records and *blocked* is the number of sessions blocked
    by the scanner gate.
    """

    private_dir = config.repo_dir / "data/private/chats"
    public_dir = config.repo_dir / "data/chats"
    publish_index = config.repo_dir / "data/indexes/publish.parquet"

    private_sessions = read_private_chats(private_dir)

    decision_map = read_latest_decisions(config=config)

    secret_store = SecretStore(config.repo_dir / "data/private/secrets")
    scrubber = _Scrubber(secret_store)

    # Phase A — deterministic secret replacement on everything
    phase_a_sessions = {
        chat_id: _sanitize_session(session, scrubber, phase_b=False)
        for chat_id, session in private_sessions.items()
        if _should_publish(chat_id, decision_map, config.default_publish_decision)
    }

    # Phase B — PII redaction on public copy only
    sanitized_sessions = {
        chat_id: _sanitize_session(session, scrubber, phase_b=True)
        for chat_id, session in phase_a_sessions.items()
    }

    blocked_count = 0

    # Scanner gate — detect missed secrets in Phase A output
    if not no_scan:
        scanner_config = ScannerConfig(
            report_dir=config.repo_dir / _REPORTS_SUBDIR,
        )
        reports = scan_sessions(phase_a_sessions, scanner_config)
        blocked_ids = {
            session_id for session_id, report in reports.items() if report.blocked
        }
        blocked_count = len(blocked_ids)
        if blocked_ids:
            import logging  # noqa: PLC0415

            logger = logging.getLogger(__name__)
            for session_id in sorted(blocked_ids):
                logger.warning(
                    "Scanner blocked session %s from publication",
                    session_id,
                )
            # Remove blocked sessions from public output
            sanitized_sessions = {
                chat_id: session
                for chat_id, session in sanitized_sessions.items()
                if chat_id not in blocked_ids
            }

    # Deny pattern check
    if config.deny_patterns:
        sanitized_sessions = {
            chat_id: session
            for chat_id, session in sanitized_sessions.items()
            if not _check_deny_patterns(session, config.deny_patterns)
        }

    existing_index = read_parquet_dataframe(publish_index)
    old_map = _index_map(existing_index)

    new_rows: list[dict[str, object]] = []
    new_index_rows: list[dict[str, str]] = []
    changed = 0
    for chat_id, session in sorted(sanitized_sessions.items()):
        content_hash = compute_content_hash(session)
        if old_map.get(chat_id) != content_hash:
            changed += 1
        new_rows.append(
            {
                "chat_id": session.id,
                "source": session.source,
                "timestamp": session.timestamp.isoformat(),
                "model": session.model,
                "messages": [
                    message.model_dump(mode="json") for message in session.messages
                ],
                "tags": session.tags,
                "content_hash": content_hash,
            }
        )
        new_index_rows.append({"chat_id": session.id, "content_hash": content_hash})

    if changed == 0 and len(old_map) == len(new_index_rows):
        return 0, blocked_count

    frame = pd.DataFrame(new_rows)
    write_partitioned_parquet(public_dir, frame, max_bytes=config.chunk_size_bytes)
    write_index_dataframe(publish_index, pd.DataFrame(new_index_rows))
    return changed, blocked_count


def pack_private_chats(config: TracerConfig) -> int:
    """Pack decided private chats from JSON into efficient Parquet storage.

    Reads all private chats, filters to those with a decision (``accepted``
    or ``rejected``), writes them into partitioned Parquet files using the
    same code path as the public dataset, and deletes the original JSON
    files to reclaim space.

    Returns the number of packed chat sessions.
    """

    private_dir = config.repo_dir / "data/private/chats"
    private_sessions = read_private_chats(private_dir)
    decision_map = read_latest_decisions(config=config)

    decided = {
        chat_id: session
        for chat_id, session in private_sessions.items()
        if decision_map.get(chat_id) in {"accepted", "rejected"}
    }

    if not decided:
        return 0

    rows = [
        {
            "chat_id": session.id,
            "timestamp": session.timestamp.isoformat(),
            "data_json": json.dumps(
                session.model_dump(mode="json"), ensure_ascii=False
            ),
        }
        for _, session in sorted(decided.items())
    ]

    frame = pd.DataFrame(rows)
    write_partitioned_parquet(private_dir, frame, max_bytes=config.chunk_size_bytes)

    for chat_id in decided:
        delete_private_chat(private_dir, chat_id)

    return len(decided)


def unpack_private_chats(
    config: TracerConfig,
    chat_ids: frozenset[str] | None = None,
) -> int:
    """Restore packed private chats from Parquet back to JSON files.

    If *chat_ids* is *None*, restores all packed chats.
    Otherwise restores only the specified chat IDs.

    Leaves Parquet files intact.
    Returns the number of chats restored.
    """

    private_dir = config.repo_dir / "data/private/chats"
    parquet_files = list_parquet_files(private_dir)

    if not parquet_files:
        return 0

    frames = [read_parquet_dataframe(p) for p in parquet_files]
    combined = pd.concat(frames, ignore_index=True)

    if chat_ids is not None:
        combined = combined[combined["chat_id"].isin(chat_ids)]

    if combined.empty:
        return 0

    restored = 0
    for _, row in combined.iterrows():
        session = ChatSession.model_validate_json(row["data_json"])
        write_private_chat(private_dir, session)
        restored += 1

    return restored
