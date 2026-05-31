"""Ollama local prompt-history adapter implementation.

Ollama does not persist full chat transcripts by default, but the CLI keeps a
readline-style prompt history at `~/.ollama/history`.
"""

from datetime import UTC, datetime
from pathlib import Path

from llm_tracer.adapters.base import BaseAdapter
from llm_tracer.schema import AttachmentPolicy
from llm_tracer.schema.v1 import ChatSessionV1

"""Public symbols exported by this module."""
__all__ = ("OllamaAdapter",)


class OllamaAdapter(BaseAdapter):
    """Normalize Ollama readline history lines into ``ChatSessionV1`` records."""

    source_slug = "ollama"

    def default_roots(self, *, options: dict[str, str]) -> list[Path]:
        """Return default Ollama home roots."""

        del options
        return [Path.home() / ".ollama"]

    def ingest(self, root: Path, patterns: list[str]) -> list[ChatSessionV1]:
        """Ingest Ollama prompt history from `history` files under the root."""

        del patterns
        history_paths: list[Path] = []
        if root.is_file() and root.name == "history":
            history_paths.append(root)
        else:
            direct = root / "history"
            if direct.exists():
                history_paths.append(direct)
            history_paths.extend(
                path for path in root.rglob("history") if path.is_file()
            )

        sessions: list[ChatSessionV1] = []
        for history_path in sorted(set(history_paths)):
            sessions.extend(_ingest_history_file(self, history_path, root))
        return sessions


def _ingest_history_file(
    adapter: OllamaAdapter,
    history_path: Path,
    root: Path,
) -> list[ChatSessionV1]:
    """Convert one Ollama `history` file into prompt-only sessions."""

    lines = [
        line.strip()
        for line in history_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not lines:
        return []

    timestamp = datetime.fromtimestamp(history_path.stat().st_mtime, tz=UTC)
    folder = history_path.parent.name if history_path.parent != root else None
    sessions: list[ChatSessionV1] = []
    for index, line in enumerate(lines, start=1):
        messages = adapter.parse_messages(
            [{"role": "user", "content": line}],
            attachment_policy=AttachmentPolicy.METADATA_ONLY,
        )
        if not messages:
            continue
        sessions.append(
            adapter.build_chat_session(  # type: ignore[arg-type]
                source_record_id=f"{history_path.name}:{index}",
                source_path=history_path,
                source_root=root,
                timestamp=timestamp,
                model="unknown",
                messages=messages,
                tags=[],
                title=None,
                folder=folder,
                attachment_policy=AttachmentPolicy.METADATA_ONLY,
            )
        )
    return sessions
