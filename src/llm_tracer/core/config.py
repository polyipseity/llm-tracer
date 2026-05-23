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

    root: Path = Field(..., description="Filesystem root for source imports.")
    patterns: list[str] = Field(
        default_factory=lambda: ["**/*.json", "**/*.jsonl"],
        description="Glob patterns used by adapters to find input files.",
    )


class HuggingFaceConfig(BaseModel):
    """Optional Hugging Face dataset sync configuration."""

    enabled: bool = Field(default=False)
    repo_id: str | None = Field(
        default=None, description="Target dataset repository ID."
    )
    token_env_var: str = Field(
        default="HF_TOKEN",
        description="Environment variable name containing the HF token.",
    )
    revision: str = Field(default="main", description="Target branch or revision.")


class TracerConfig(BaseModel):
    """Top-level runtime configuration for decoupled data repository workflows."""

    repo_dir: Path = Field(
        ..., description="Path to the separate data repository working tree."
    )
    chunk_size_bytes: int = Field(
        default=10_000_000,
        ge=1,
        description="Maximum size target per tracked chunk file.",
    )
    sources: dict[str, SourceConfig] = Field(default_factory=dict)
    hf: HuggingFaceConfig = Field(default_factory=HuggingFaceConfig)


def _resolve_path(base: Path, value: Path) -> Path:
    """Resolve a potentially relative path against config directory."""

    if value.is_absolute():
        return value
    return (base / value).resolve()


def _resolve_config_paths(config: TracerConfig, *, config_dir: Path) -> TracerConfig:
    """Return a copy of config with all filesystem paths resolved."""

    resolved_sources = {
        name: SourceConfig(
            root=_resolve_path(config_dir, source.root),
            patterns=source.patterns,
        )
        for name, source in config.sources.items()
    }
    return TracerConfig(
        repo_dir=_resolve_path(config_dir, config.repo_dir),
        chunk_size_bytes=config.chunk_size_bytes,
        sources=resolved_sources,
        hf=config.hf,
    )


def load_config(path: Path) -> TracerConfig:
    """Load and validate runtime config from a TOML file path."""

    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    config = TracerConfig.model_validate(raw)
    return _resolve_config_paths(config, config_dir=path.parent)


def default_config_template() -> str:
    """Return a minimal default `llm-tracer.toml` template content."""

    return """repo_dir = \".\"
chunk_size_bytes = 10000000

[hf]
enabled = false
repo_id = \"\"
token_env_var = \"HF_TOKEN\"
revision = \"main\"

[sources.lmstudio]
root = \"./imports/lmstudio\"
patterns = [\"**/*.json\", \"**/*.jsonl\"]

[sources.copilot]
root = \"./imports/copilot\"
patterns = [\"**/*.json\", \"**/*.jsonl\"]

[sources.pi_agent]
root = \"./imports/pi-agent\"
patterns = [\"**/*.json\", \"**/*.jsonl\"]
"""
