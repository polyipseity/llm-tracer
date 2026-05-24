"""Base adapter abstractions for source-specific chat ingestion."""

import json
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from llm_tracer.core.hashing import compute_chat_id, compute_ingest_key
from llm_tracer.core.schema import ChatSession, Message
from llm_tracer.core.tags import normalize_tags

"""Public symbols exported by this module."""
__all__ = ("BaseAdapter",)


class BaseAdapter(ABC):
    """Abstract adapter that normalizes source records into `ChatSession` values."""

    source_slug: str

    @abstractmethod
    def ingest(self, root: Path, patterns: list[str]) -> list[ChatSession]:
        """Parse source files from a root directory and return normalized chats."""

    def default_roots(self, *, options: dict[str, str]) -> list[Path]:
        """Return default import roots when config does not provide one."""

        del options
        return []

    def ingest_with_options(
        self,
        *,
        root: Path | None,
        patterns: list[str],
        options: dict[str, str],
    ) -> list[ChatSession]:
        """Ingest from either configured root or adapter-defined default roots."""

        search_roots = (
            [root] if root is not None else self.default_roots(options=options)
        )
        sessions: list[ChatSession] = []
        for search_root in search_roots:
            sessions.extend(self.ingest(search_root, patterns))
        return sessions

    def discover_files(self, root: Path, patterns: list[str]) -> list[Path]:
        """Return source files matching configured glob patterns."""

        discovered: set[Path] = set()
        for pattern in patterns:
            for path in root.glob(pattern):
                if path.is_file() and path.suffix.lower() in {".json", ".jsonl"}:
                    discovered.add(path)
        return sorted(discovered)

    def parse_json_payloads(self, file_path: Path) -> list[dict[str, Any]]:
        """Parse JSON or JSONL source file into a list of dict payloads."""

        if file_path.suffix.lower() == ".jsonl":
            payloads: list[dict[str, Any]] = []
            with file_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    row = line.strip()
                    if not row:
                        continue
                    payload = json.loads(row)
                    if isinstance(payload, dict):
                        payloads.append(payload)
            return payloads
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            return [payload]
        return []

    def build_import_tags(
        self,
        *,
        source_record_id: str,
        title: str | None,
        folder: str | None,
    ) -> list[str]:
        """Build normalized import tags for one chat session."""

        import_id = _normalize_tag_component(source_record_id)
        tags = [f"import/id/{self.source_slug}/{import_id}"]
        if title is not None:
            tags.append(f"import/title/{_normalize_tag_component(title)}")
        if folder is not None:
            tags.append(f"import/workspace/{_normalize_tag_component(folder)}")
        return tags

    def build_chat_session(
        self,
        *,
        source_record_id: str,
        source_path: Path,
        source_root: Path,
        timestamp: datetime,
        model: str,
        messages: list[Message],
        tags: list[str],
        title: str | None = None,
        folder: str | None = None,
    ) -> ChatSession:
        """Construct a validated `ChatSession` with deterministic identity fields."""

        normalized_timestamp = timestamp.astimezone(UTC)
        import_tags = self.build_import_tags(
            source_record_id=source_record_id,
            title=title,
            folder=folder or source_path.parent.name,
        )
        merged_tags = normalize_tags([*tags, *import_tags])
        draft = ChatSession(
            id="",
            source=self.source_slug,
            timestamp=normalized_timestamp,
            model=model,
            messages=messages,
            tags=merged_tags,
            source_record_id=source_record_id,
            ingest_key=compute_ingest_key(
                source=self.source_slug,
                source_record_id=source_record_id,
                source_path=source_path,
            ),
        )
        draft.id = compute_chat_id(draft)
        return draft

    def parse_messages(self, payload: Any) -> list[Message]:
        """Normalize message-like payloads into schema `Message` objects."""

        if not isinstance(payload, list):
            return []
        result: list[Message] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "assistant")).strip() or "assistant"
            content = str(item.get("content", "")).strip()
            if not content:
                continue
            tool_calls_raw = item.get("tool_calls")
            tool_calls: list[dict[str, Any]] | None
            if isinstance(tool_calls_raw, list):
                tool_calls = [x for x in tool_calls_raw if isinstance(x, dict)]
            else:
                tool_calls = None
            native_id_raw = item.get("native_id")
            native_id: str | None = (
                str(native_id_raw).strip() or None
                if native_id_raw is not None
                else None
            )
            result.append(
                Message(
                    role=role,
                    content=content,
                    tool_calls=tool_calls,
                    native_id=native_id,
                )
            )
        return result


def _normalize_tag_component(value: str) -> str:
    """Normalize one dynamic tag component into a valid non-empty value."""

    cleaned = " ".join(value.strip().split())
    cleaned = cleaned.replace("/", "_").replace("\\", "_")
    return cleaned or "unknown"
