"""Sanitization and publish engine from private JSONL to public Parquet partitions."""

import re
from importlib import import_module
from importlib.util import find_spec

import pandas as pd

from llm_tracer.core.config import TracerConfig
from llm_tracer.core.hashing import compute_content_hash
from llm_tracer.core.schema import ChatSession
from llm_tracer.core.storage import (
    read_parquet_dataframe,
    read_partitioned_private_chats,
    write_index_dataframe,
    write_partitioned_parquet,
)

"""Public symbols exported by this module."""
__all__ = ("publish_sanitized",)


"""Fallback secret-like token pattern used when Presidio is unavailable."""
_SECRET_PATTERN = re.compile(r"\b(?:sk|hf|ghp|xoxb)-[A-Za-z0-9_-]{8,}\b")


"""Fallback email pattern used when Presidio is unavailable."""
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


if (
    find_spec("presidio_analyzer") is not None
    and find_spec("presidio_anonymizer") is not None
):
    """Runtime indicator that Presidio modules are available."""
    _PRESIDIO_AVAILABLE = True
else:  # pragma: no cover - optional dependency
    """Runtime indicator that Presidio modules are unavailable."""
    _PRESIDIO_AVAILABLE = False


class _Scrubber:
    """Text scrubber that prefers Presidio and falls back to regex replacements."""

    def __init__(self) -> None:
        """Initialize optional Presidio components lazily."""

        self._analyzer = None
        self._anonymizer = None
        if _PRESIDIO_AVAILABLE:
            analyzer_module = import_module("presidio_analyzer")
            anonymizer_module = import_module("presidio_anonymizer")
            analyzer_type = getattr(analyzer_module, "AnalyzerEngine")
            anonymizer_type = getattr(anonymizer_module, "AnonymizerEngine")
            self._analyzer = analyzer_type()
            self._anonymizer = anonymizer_type()

    def scrub_text(self, text: str) -> str:
        """Sanitize a text field and return redacted output."""

        if self._analyzer is not None and self._anonymizer is not None:
            results = self._analyzer.analyze(text=text, language="en")
            if results:
                anonymized = self._anonymizer.anonymize(
                    text=text, analyzer_results=results
                )
                text = anonymized.text
        text = _SECRET_PATTERN.sub("<REDACTED_SECRET>", text)
        text = _EMAIL_PATTERN.sub("<REDACTED_PII>", text)
        return text


def _sanitize_session(session: ChatSession, scrubber: _Scrubber) -> ChatSession:
    """Return a sanitized copy of one chat session."""

    sanitized_messages = [
        message.model_copy(update={"content": scrubber.scrub_text(message.content)})
        for message in session.messages
    ]
    return session.model_copy(update={"messages": sanitized_messages})


def _index_map(frame: pd.DataFrame) -> dict[str, str]:
    """Build `chat_id -> content_hash` mapping from a publish index frame."""

    if frame.empty or "chat_id" not in frame or "content_hash" not in frame:
        return {}
    rows = frame[["chat_id", "content_hash"]].to_dict(orient="records")
    return {str(row["chat_id"]): str(row["content_hash"]) for row in rows}


def publish_sanitized(config: TracerConfig) -> int:
    """Publish sanitized chats from private store into tracked partitioned parquet.

    Returns the number of changed chat records (inserted or updated) compared
    with the current publish index.
    """

    private_dir = config.repo_dir / "data/private/chats"
    public_dir = config.repo_dir / "data/chats"
    publish_index = config.repo_dir / "data/indexes/publish.parquet"

    private_sessions = read_partitioned_private_chats(private_dir)
    scrubber = _Scrubber()
    sanitized_sessions = {
        chat_id: _sanitize_session(session, scrubber)
        for chat_id, session in private_sessions.items()
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
        return 0

    frame = pd.DataFrame(new_rows)
    write_partitioned_parquet(public_dir, frame, max_bytes=config.chunk_size_bytes)
    write_index_dataframe(publish_index, pd.DataFrame(new_index_rows))
    return changed
