"""Filesystem storage helpers for JSONL/Parquet partitioned datasets."""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from llm_tracer.core.schema import ChatSession

"""Public symbols exported by this module."""
__all__ = (
    "build_day_partition_path",
    "ensure_dir",
    "list_jsonl_files",
    "list_parquet_files",
    "read_jsonl_records",
    "read_partitioned_private_chats",
    "read_parquet_dataframe",
    "write_index_dataframe",
    "write_partitioned_jsonl",
    "write_partitioned_parquet",
)


"""File naming prefix for partition chunk files."""
_PART_PREFIX = "part-"


def ensure_dir(path: Path) -> None:
    """Create a directory tree if it does not exist."""

    path.mkdir(parents=True, exist_ok=True)


def build_day_partition_path(root: Path, timestamp: pd.Timestamp) -> Path:
    """Build `YYYY/MM/DD` partition path from a timestamp."""

    day = timestamp.tz_convert("UTC") if timestamp.tz is not None else timestamp
    return root / f"{day.year:04d}" / f"{day.month:02d}" / f"{day.day:02d}"


def list_jsonl_files(root: Path) -> list[Path]:
    """Return all JSONL files under a root in deterministic order."""

    if not root.exists():
        return []
    return sorted(root.rglob("*.jsonl"))


def list_parquet_files(root: Path) -> list[Path]:
    """Return all Parquet files under a root in deterministic order."""

    if not root.exists():
        return []
    return sorted(root.rglob("*.parquet"))


def read_jsonl_records(path: Path) -> list[dict[str, Any]]:
    """Read JSONL records from one file path."""

    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            records.append(json.loads(raw))
    return records


def read_partitioned_private_chats(root: Path) -> dict[str, ChatSession]:
    """Read all private chat JSONL records and key them by chat id."""

    result: dict[str, ChatSession] = {}
    for file in list_jsonl_files(root):
        for row in read_jsonl_records(file):
            session = ChatSession.model_validate(row)
            result[session.id] = session
    return result


def _partition_rows_by_day(
    rows: list[dict[str, Any]],
) -> dict[tuple[int, int, int], list[dict[str, Any]]]:
    """Group rows by UTC `(year, month, day)` tuples."""

    grouped: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        timestamp = pd.Timestamp(row["timestamp"]).tz_convert("UTC")
        key = (int(timestamp.year), int(timestamp.month), int(timestamp.day))
        grouped[key].append(row)
    return grouped


def _rotate_jsonl_chunks(
    partition_dir: Path,
    rows: list[dict[str, Any]],
    *,
    max_bytes: int,
) -> None:
    """Write rows into `part-*.jsonl` files under a size threshold."""

    ensure_dir(partition_dir)
    chunk_index = 0
    chunk_bytes = 0
    handle = None
    try:
        for row in rows:
            encoded = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
            if handle is None or (
                chunk_bytes + len(encoded) > max_bytes and chunk_bytes > 0
            ):
                if handle is not None:
                    handle.close()
                output = partition_dir / f"{_PART_PREFIX}{chunk_index:05d}.jsonl"
                handle = output.open("wb")
                chunk_index += 1
                chunk_bytes = 0
            handle.write(encoded)
            chunk_bytes += len(encoded)
    finally:
        if handle is not None:
            handle.close()


def write_partitioned_jsonl(
    root: Path,
    rows: list[dict[str, Any]],
    *,
    max_bytes: int,
) -> None:
    """Rewrite a partitioned JSONL dataset with deterministic chunking."""

    if root.exists():
        for old_file in list_jsonl_files(root):
            old_file.unlink()
    grouped = _partition_rows_by_day(rows)
    for (year, month, day), partition_rows in sorted(grouped.items()):
        partition = root / f"{year:04d}" / f"{month:02d}" / f"{day:02d}"
        _rotate_jsonl_chunks(partition, partition_rows, max_bytes=max_bytes)


def _rotate_parquet_chunks(
    partition_dir: Path,
    frame: pd.DataFrame,
    *,
    max_bytes: int,
) -> None:
    """Write a dataframe into `part-*.parquet` files under a size threshold."""

    ensure_dir(partition_dir)
    rows = frame.to_dict(orient="records")
    if not rows:
        return
    batch: list[dict[str, Any]] = []
    batch_index = 0
    for row in rows:
        candidate = pd.DataFrame(batch + [row])
        output = partition_dir / f"{_PART_PREFIX}{batch_index:05d}.parquet"
        candidate.to_parquet(output, index=False)
        if output.stat().st_size > max_bytes and batch:
            output.unlink(missing_ok=True)
            pd.DataFrame(batch).to_parquet(output, index=False)
            batch_index += 1
            batch = [row]
        else:
            batch.append(row)
    if batch:
        output = partition_dir / f"{_PART_PREFIX}{batch_index:05d}.parquet"
        pd.DataFrame(batch).to_parquet(output, index=False)


def write_partitioned_parquet(
    root: Path,
    frame: pd.DataFrame,
    *,
    max_bytes: int,
) -> None:
    """Rewrite a partitioned Parquet dataset with deterministic chunking."""

    if root.exists():
        for old_file in list_parquet_files(root):
            old_file.unlink()
    if frame.empty:
        return
    grouped_rows = _partition_rows_by_day(frame.to_dict(orient="records"))
    for (year, month, day), rows in sorted(grouped_rows.items()):
        partition = root / f"{year:04d}" / f"{month:02d}" / f"{day:02d}"
        output_group = pd.DataFrame(rows)
        _rotate_parquet_chunks(partition, output_group, max_bytes=max_bytes)


def read_parquet_dataframe(path: Path) -> pd.DataFrame:
    """Read a parquet index dataframe or return an empty frame when missing."""

    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def write_index_dataframe(path: Path, frame: pd.DataFrame) -> None:
    """Persist an index dataframe, creating parent directories as needed."""

    ensure_dir(path.parent)
    frame.to_parquet(path, index=False)
