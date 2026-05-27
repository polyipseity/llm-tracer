"""Sync backends for publishing traces to remote repositories and datasets."""

from llm_tracer.config import TracerConfig
from llm_tracer.sync.git import sync_public_repo
from llm_tracer.sync.hugging_face import sync_hugging_face

"""Public symbols exported by this module."""
__all__ = (
    "sync_all",
    "sync_hugging_face",
    "sync_public_repo",
)


def sync_all(config: TracerConfig) -> int:
    """Run all enabled sync backends and return a combined exit code."""
    return sync_hugging_face(config)
