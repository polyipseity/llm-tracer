"""Runtime configuration models and loader for llm-tracer."""

import json
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

"""Public symbols exported by this module."""
__all__ = (
    "HuggingFaceConfig",
    "SourceConfig",
    "TracerConfig",
    "default_config_template",
    "load_config",
)


class SourceConfig(BaseModel):
    """Configuration for one import source root."""

    root: Path | None = Field(
        default=None,
        description="Optional filesystem root override for source imports.",
    )
    patterns: list[str] = Field(
        default_factory=lambda: ["**/*.json", "**/*.jsonl"],
        description="Glob patterns used by adapters to find input files.",
    )
    options: dict[str, str] = Field(
        default_factory=dict,
        description="Adapter-specific options for import behavior.",
    )


class HuggingFaceConfig(BaseModel):
    """Optional Hugging Face dataset sync configuration."""

    enabled: bool = Field(default=False)
    repo_id: str | None = Field(
        default=None, description="Target dataset repository ID."
    )
    token_env_var: str = Field(
        default="HUGGING_FACE_TOKEN",
        description="Environment variable name containing the Hugging Face token.",
    )
    revision: str = Field(default="main", description="Target branch or revision.")


class TracerConfig(BaseModel):
    """Top-level runtime configuration for decoupled data repository workflows."""

    repo_dir: Path = Field(
        ..., description="Path to the separate data repository working tree."
    )
    chunk_size_bytes: int = Field(
        default=1_000_000,
        ge=1,
        description="Maximum size target per tracked chunk file.",
    )
    sources: dict[str, SourceConfig] = Field(default_factory=dict)
    hugging_face: HuggingFaceConfig = Field(default_factory=HuggingFaceConfig)
    default_publish_decision: Literal["accept", "reject"] = Field(
        default="reject",
        description="Policy applied to chats without an explicit accepted or rejected decision.",
    )


def _resolve_path(base: Path, value: Path) -> Path:
    """Resolve a potentially relative path against config directory."""

    if value.is_absolute():
        return value
    return (base / value).resolve()


def _resolve_config_paths(config: TracerConfig, *, config_dir: Path) -> TracerConfig:
    """Return a copy of config with all filesystem paths resolved."""

    resolved_sources = {
        name: SourceConfig(
            root=(
                _resolve_path(config_dir, source.root)
                if source.root is not None
                else None
            ),
            patterns=source.patterns,
            options=source.options,
        )
        for name, source in config.sources.items()
    }
    return TracerConfig(
        repo_dir=_resolve_path(config_dir, config.repo_dir),
        chunk_size_bytes=config.chunk_size_bytes,
        sources=resolved_sources,
        hugging_face=config.hugging_face,
        default_publish_decision=config.default_publish_decision,
    )


def load_config(path: Path) -> TracerConfig:
    """Load and validate runtime config from a TOML file path."""

    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    config = TracerConfig.model_validate(raw)
    return _resolve_config_paths(config, config_dir=path.parent)


def default_config_template(repo_dir: Path = Path(".")) -> str:
    """Return a minimal default `llm-tracer.toml` template content."""

    repo_dir_literal = json.dumps(str(repo_dir))
    return f"""repo_dir = {repo_dir_literal}
chunk_size_bytes = 1000000
default_publish_decision = \"reject\"

[sources.lmstudio]
# root auto-detected to ~/.lmstudio/conversations/

[sources.vscode]
# root auto-detected per platform for Code and Code - Insiders

[sources.pi_coding_agent]
# root auto-detected to ~/.pi/agent

[sources.opencode]
# root auto-detected to XDG data storage (usually ~/.local/share/opencode/storage)

# Uncomment and set root only when using the generic local adapter.
#[sources.local]
#root = \"./imports\"
#patterns = [\"**/*.json\", \"**/*.jsonl\"]

[hugging_face]
enabled = false
repo_id = \"\"
token_env_var = \"HUGGING_FACE_TOKEN\"
revision = \"main\"
"""
