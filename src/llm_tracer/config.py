"""Runtime configuration models and loader for llm-tracer."""

import tomllib
from pathlib import Path

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
    )


def load_config(path: Path) -> TracerConfig:
    """Load and validate runtime config from a TOML file path."""

    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    config = TracerConfig.model_validate(raw)
    return _resolve_config_paths(config, config_dir=path.parent)


def default_config_template() -> str:
    """Return a minimal default `llm-tracer.toml` template content."""

    return """repo_dir = \".\"
chunk_size_bytes = 1000000

[hugging_face]
enabled = false
repo_id = \"\"
token_env_var = \"HUGGING_FACE_TOKEN\"
revision = \"main\"

[sources.lmstudio]
root = \"./imports/lmstudio\"
patterns = [\"**/*.json\", \"**/*.jsonl\"]

[sources.vscode]
root = \"./imports/vscode\"
patterns = [\"**/*.json\", \"**/*.jsonl\"]

[sources.pi_coding_agent]
root = \"./imports/pi-coding-agent\"
patterns = [\"**/*.json\", \"**/*.jsonl\"]

[sources.opencode]
root = \"./imports/opencode\"
patterns = [\"**/*.json\", \"**/*.jsonl\"]

[sources.local]
root = \"./imports\"
patterns = [\"**/*.json\", \"**/*.jsonl\"]
"""
