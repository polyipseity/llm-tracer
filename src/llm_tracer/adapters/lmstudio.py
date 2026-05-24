"""LM Studio conversation adapter implementation.

LM Studio stores chat conversations as JSON files in
``~/.lmstudio/conversations/<subfolder>/`` on macOS/Linux, and
``%USERPROFILE%\\.lmstudio\\conversations\\<subfolder>\\`` on Windows.
Files are named ``<epoch-ms>.conversation.json`` where the epoch-ms
portion is the conversation identifier — the JSON body contains no
top-level ``id`` field.

Top-level JSON schema::

    name         – conversation title (string)
    createdAt    – creation time, epoch milliseconds (integer)
    tokenCount   – cumulative token count (integer)
    systemPrompt – system prompt (string, may be empty)
    pinned       – boolean
    messages     – list of turn containers (see below)

Each turn container::

    versions          – list of version objects (edits / regenerations)
    currentlySelected – index into versions[] (integer, usually 0)

Each version::

    role         – "user" | "assistant" | "system" | "tool"
    content      – list of content parts: [{"type": "text", "text": "..."}]
    preprocessed – {"timestamp": <epoch_ms>}
    steps        – (assistant only) list of generation steps

Each generation step (assistant messages)::

    genInfo.indexedModelIdentifier – model identifier string
      e.g. "lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF/..."

Sources
-------
- LM Studio chat docs: https://lmstudio.ai/docs/app/basics/chat
- Official SDK type definitions (ChatHistoryData):
  https://github.com/lmstudio-ai/lmstudio-js/blob/main/packages/lms-shared-types/src/ChatHistoryData.ts
- Real-file converter confirming versioned schema:
  https://github.com/skiretic/lmstudiochatconverter
- File naming convention confirmed by:
  https://github.com/ispaure/migration-chatgpt-to-lmstudio
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from llm_tracer.adapters.base import BaseAdapter
from llm_tracer.core.schema import ChatSession

"""Public symbols exported by this module."""
__all__ = ("LMStudioAdapter",)


class LMStudioAdapter(BaseAdapter):
    """Normalize LM Studio conversation files into ``ChatSession`` records."""

    source_slug = "lmstudio"

    def default_roots(self, *, options: dict[str, str]) -> list[Path]:
        """Return default LM Studio conversation directories."""

        del options
        home = Path.home()
        return [
            home / ".lmstudio" / "conversations",
            home / "Library/Application Support/LM Studio",
        ]

    def ingest(self, root: Path, patterns: list[str]) -> list[ChatSession]:
        """Ingest and normalize LM Studio conversation files from a root directory."""

        sessions: list[ChatSession] = []
        for source_path in self.discover_files(root, patterns):
            for payload in self.parse_json_payloads(source_path):
                timestamp = _parse_created_at(payload.get("createdAt"), source_path)
                if timestamp is None:
                    continue
                title = payload.get("name") or payload.get("title")
                source_record_id = str(
                    payload.get("id")
                    or payload.get("conversation_id")
                    or payload.get("thread_id")
                    or _stem_id(source_path)
                )
                raw_messages: Any = (
                    payload.get("messages") or payload.get("conversation") or []
                )
                normalized = _normalize_messages(raw_messages)
                messages = self.parse_messages(normalized)
                if not messages:
                    continue
                model = _extract_model(raw_messages) or "unknown"
                tags_raw = payload.get("tags")
                tags = [str(t) for t in tags_raw] if isinstance(tags_raw, list) else []
                sessions.append(
                    self.build_chat_session(
                        source_record_id=source_record_id,
                        source_path=source_path,
                        source_root=root,
                        timestamp=timestamp,
                        model=model,
                        messages=messages,
                        tags=tags,
                        title=str(title) if title is not None else None,
                    )
                )
        return sessions


def _stem_id(path: Path) -> str:
    """Derive a conversation ID from the epoch-ms portion of the filename stem."""

    first_part = path.stem.split(".")[0]
    return first_part if first_part.isdigit() else path.stem


def _parse_created_at(value: object, source_path: Path) -> datetime | None:
    """Parse ``createdAt`` (epoch ms integer or ISO string) or fall back to filename."""

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000.0, tz=UTC)
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    if isinstance(value, str):
        cleaned = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(cleaned).astimezone(UTC)
        except ValueError:
            pass
    stem_part = _stem_id(source_path)
    if stem_part.isdigit():
        try:
            return datetime.fromtimestamp(int(stem_part) / 1000.0, tz=UTC)
        except ValueError, OSError:
            pass
    return None


def _normalize_messages(raw: Any) -> list[dict[str, Any]]:
    """Flatten LM Studio versioned turn containers into simple {role, content} dicts."""

    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        item_d = cast("dict[str, Any]", item)
        if "versions" in item_d:
            versions: Any = item_d["versions"]
            if not isinstance(versions, list) or not versions:
                continue
            idx = item_d.get("currentlySelected", 0)
            version: Any = (
                versions[idx]
                if isinstance(idx, int) and 0 <= idx < len(versions)
                else versions[0]
            )
            if not isinstance(version, dict):
                continue
            version_d = cast("dict[str, Any]", version)
            role = str(version_d.get("role", "assistant"))
            content_raw: Any = version_d.get("content", [])
            if isinstance(content_raw, list):
                text = " ".join(
                    p.get("text", "")
                    for p in content_raw
                    if isinstance(p, dict) and p.get("type") == "text"
                ).strip()
            elif isinstance(content_raw, str):
                text = content_raw.strip()
            else:
                text = ""
            if text:
                result.append({"role": role, "content": text})
        else:
            result.append(item_d)
    return result


def _extract_model(raw: Any) -> str | None:
    """Extract model ID from the last assistant message's generation step info."""

    if not isinstance(raw, list):
        return None
    raw_list: list[Any] = raw
    for item in reversed(raw_list):
        if not isinstance(item, dict) or "versions" not in item:
            continue
        item_d = cast("dict[str, Any]", item)
        versions: Any = item_d["versions"]
        if not isinstance(versions, list) or not versions:
            continue
        idx = item_d.get("currentlySelected", 0)
        version: Any = (
            versions[idx]
            if isinstance(idx, int) and 0 <= idx < len(versions)
            else versions[0]
        )
        if not isinstance(version, dict):
            continue
        version_d = cast("dict[str, Any]", version)
        if version_d.get("role") not in ("assistant", None):
            continue
        for step in version_d.get("steps") or []:
            if not isinstance(step, dict):
                continue
            step_d = cast("dict[str, Any]", step)
            gen_info: Any = step_d.get("genInfo", {})
            if isinstance(gen_info, dict):
                gen_info_d = cast("dict[str, Any]", gen_info)
                if gen_info_d.get("indexedModelIdentifier"):
                    return str(gen_info_d["indexedModelIdentifier"])
    return None
