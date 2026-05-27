"""Local recursive adapter that delegates files to source-specific adapters."""

from pathlib import Path

from llm_tracer.adapters.base import BaseAdapter
from llm_tracer.adapters.claude_code import ClaudeCodeAdapter
from llm_tracer.adapters.codex import CodexAdapter
from llm_tracer.adapters.lmstudio import LMStudioAdapter
from llm_tracer.adapters.ollama import OllamaAdapter
from llm_tracer.adapters.opencode import OpenCodeAdapter
from llm_tracer.adapters.oterm import OTermAdapter
from llm_tracer.adapters.pi_coding_agent import PiCodingAgentAdapter
from llm_tracer.adapters.vscode import VSCodeAdapter
from llm_tracer.schema import ChatSession
from llm_tracer.utils.tags import normalize_tags

"""Public symbols exported by this module."""
__all__ = ("LocalAdapter",)


class LocalAdapter(BaseAdapter):
    """Scan a user-selected directory and delegate each file to a source adapter."""

    source_slug = "local"

    _DELEGATES: tuple[type[BaseAdapter], ...] = (
        VSCodeAdapter,
        ClaudeCodeAdapter,
        CodexAdapter,
        PiCodingAgentAdapter,
        LMStudioAdapter,
        OTermAdapter,
        OllamaAdapter,
        OpenCodeAdapter,
    )

    def ingest_with_options(
        self,
        *,
        roots: list[Path] | None,
        patterns: list[str],
        options: dict[str, str],
    ) -> list[ChatSession]:
        """Ingest from required user-specified roots for local delegation mode."""

        del options
        if not roots:
            raise ValueError("source 'local' requires configured roots")
        sessions: list[ChatSession] = []
        for root in roots:
            sessions.extend(self.ingest(root, patterns))
        return sessions

    def ingest(self, root: Path, patterns: list[str]) -> list[ChatSession]:
        """Recursively scan root and delegate each file to the first matching adapter."""

        sessions: list[ChatSession] = []
        delegates = [adapter_type() for adapter_type in self._DELEGATES]
        for source_path in self.discover_files(root, patterns):
            delegated_sessions = self._delegate_file(
                delegates=delegates,
                source_path=source_path,
            )
            if not delegated_sessions:
                continue
            local_tags = self._build_local_tags(root=root, source_path=source_path)
            for session in delegated_sessions:
                sessions.append(
                    session.model_copy(
                        update={
                            "tags": normalize_tags([*session.tags, *local_tags]),
                        }
                    )
                )
        return sessions

    def _delegate_file(
        self,
        *,
        delegates: list[BaseAdapter],
        source_path: Path,
    ) -> list[ChatSession]:
        """Delegate one source file to the first adapter that can parse it."""

        for delegate in delegates:
            delegated = delegate.ingest(source_path.parent, [source_path.name])
            if delegated:
                return delegated
        return []

    def _build_local_tags(self, *, root: Path, source_path: Path) -> list[str]:
        """Build local import tag as the file path relative to root."""

        relative_file = source_path.relative_to(root)
        return [f"import/id/local/{relative_file.as_posix()}"]
