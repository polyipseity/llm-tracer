"""Optional Hugging Face dataset sync for sanitized public artifacts."""

import os
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path

import pandas as pd

from llm_tracer.core.config import TracerConfig
from llm_tracer.core.hashing import sha256_bytes
from llm_tracer.core.storage import read_parquet_dataframe, write_index_dataframe

"""Public symbols exported by this module."""
__all__ = ("sync_hugging_face",)


if find_spec("huggingface_hub") is not None:
    """Runtime indicator that huggingface_hub is available."""
    _HF_AVAILABLE = True
else:  # pragma: no cover - optional dependency
    """Runtime indicator that huggingface_hub is unavailable."""
    _HF_AVAILABLE = False


def _hash_file(path: Path) -> str:
    """Compute SHA256 hash for a file payload."""

    return sha256_bytes(path.read_bytes())


def sync_hugging_face(config: TracerConfig) -> int:
    """Sync sanitized public chats to Hugging Face dataset repository.

    Returns the number of uploaded artifacts.
    """

    if not config.hf.enabled:
        return 0
    if not config.hf.repo_id:
        raise ValueError("hf.repo_id must be configured when HF sync is enabled")

    token = os.getenv(config.hf.token_env_var)
    if not token:
        raise ValueError(
            f"environment variable {config.hf.token_env_var!r} is required for HF sync"
        )

    if not _HF_AVAILABLE:
        raise ValueError("huggingface-hub must be installed to use sync-hf")

    hf_module = import_module("huggingface_hub")
    hf_api_type = getattr(hf_module, "HfApi")
    api = hf_api_type(token=token)
    sync_index_path = config.repo_dir / "data/indexes/hf_sync.parquet"
    existing_df = read_parquet_dataframe(sync_index_path)
    old_map = {}
    if (
        not existing_df.empty
        and "artifact_path" in existing_df
        and "content_hash" in existing_df
    ):
        rows = existing_df[["artifact_path", "content_hash"]].to_dict(orient="records")
        old_map = {str(row["artifact_path"]): str(row["content_hash"]) for row in rows}

    public_root = config.repo_dir / "data/chats"
    uploads = 0
    new_rows: list[dict[str, str]] = []
    for file in sorted(public_root.rglob("*.parquet")):
        rel = file.relative_to(config.repo_dir).as_posix()
        content_hash = _hash_file(file)
        if old_map.get(rel) != content_hash:
            api.upload_file(
                path_or_fileobj=str(file),
                path_in_repo=rel,
                repo_id=config.hf.repo_id,
                repo_type="dataset",
                revision=config.hf.revision,
            )
            uploads += 1
        new_rows.append(
            {
                "artifact_path": rel,
                "content_hash": content_hash,
                "revision": config.hf.revision,
            }
        )

    write_index_dataframe(sync_index_path, pd.DataFrame(new_rows))
    return uploads
