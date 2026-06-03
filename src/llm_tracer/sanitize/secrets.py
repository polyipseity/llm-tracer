"""Deterministic secret store for literal-value redaction.

The SecretStore manages a set of known literal secrets in
``data/private/secrets/`` and provides longest-first matching for replacement.

Store layout::

    data/private/secrets/
    ├── known.txt        # one literal secret per line, sorted at read time
    └── env.json         # metadata about env-file sources (last scan time, paths)

Binary secrets that fail UTF-8 decode are stored as base64; matching tries
both raw bytes and base64-encoded occurrences.
"""

import base64
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from llm_tracer.utils.hashing import hash_bytes

"""Public symbols exported by this module."""
__all__ = (
    "SecretStore",
    "looks_sensitive_name",
    "parse_env_file",
    "scan_env_file",
)


"""Default subdirectory for secret store files within the private data tree."""
_SECRETS_SUBDIR = "secrets"

"""File name for line-separated literal secrets."""
_KNOWN_FILE = "known.txt"

"""File name for env-file scanning metadata."""
_ENV_META_FILE = "env.json"

"""Replacement pattern for redacted secrets."""
_REDACTED_FORMAT = "[REDACTED_SECRET_{}]"

"""Line prefix for base64-encoded multiline secrets in known.txt."""
_B64_PREFIX = "b64:"

"""Maximum allowed secret size in bytes (1 MiB)."""
_MAX_SECRET_SIZE = 1_048_576


def _load_known(path: Path) -> tuple[list[str], list[bytes]]:
    """Load literal secrets from *path*, returning (text_secrets, binary_secrets).

    Lines starting with ``b64:`` are decoded as base64-encoded secrets
    (both multiline text and binary). Other lines are treated as plain text;
    plain-text lines that happen to be valid non-trivial base64 are also
    added to *binary_secrets* for backward-compatible matching.
    """

    if not path.exists():
        return [], []
    text_secrets: list[str] = []
    binary_secrets: list[bytes] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(_B64_PREFIX):
            encoded = line[len(_B64_PREFIX) :]
            try:
                decoded = base64.b64decode(encoded, validate=True)
            except ValueError:
                text_secrets.append(line)
                continue
            try:
                text_secrets.append(decoded.decode("utf-8"))
            except UnicodeDecodeError:
                binary_secrets.append(decoded)
            continue
        # Plain text line
        text_secrets.append(line)
        # If it looks like a base64-encoded binary, add decoded version
        try:
            decoded = base64.b64decode(line, validate=True)
            if decoded != line.encode("utf-8"):
                binary_secrets.append(decoded)
        except ValueError:
            pass
    return text_secrets, binary_secrets


def _sort_descending(secrets: list[str]) -> list[str]:
    """Sort secrets descending by length (longest-first for greedy matching)."""

    return sorted(set(secrets), key=lambda s: (-len(s), s))


def _replace_literals(text: str, secrets: list[str]) -> str:
    """Replace all occurrences of *secrets* in *text* with redacted markers.

    Secrets are assumed pre-sorted longest-first so longer matches take
    priority over shorter ones contained within them.
    """

    for secret in secrets:
        if secret not in text:
            continue
        prefix = hash_bytes(secret.encode("utf-8"))[:12]
        replacement = _REDACTED_FORMAT.format(prefix)
        text = text.replace(secret, replacement)
    return text


def _replace_binary(text: str, binary_secrets: list[bytes]) -> str:
    """Replace base64-encoded occurrences of binary secrets in *text*."""

    for secret in binary_secrets:
        encoded = base64.b64encode(secret).decode("ascii")
        if encoded in text:
            prefix = hash_bytes(secret)[:12]
            replacement = _REDACTED_FORMAT.format(prefix)
            text = text.replace(encoded, replacement)
    return text


def looks_sensitive_name(name: str) -> bool:
    """Heuristic check: does *name* look like a sensitive env-var name?

    Ported from pi-share-hf ``secrets.ts`` ``looksSensitiveName``.
    """

    upper = name.upper()
    sensitive_keywords = (
        "TOKEN",
        "SECRET",
        "KEY",
        "PASSWORD",
        "PASS",
        "API_KEY",
        "APIKEY",
        "APISECRET",
        "PRIVATE_KEY",
        "ACCESS_KEY",
        "SECRET_KEY",
        "AUTH",
        "CREDENTIAL",
        "SIGNING_KEY",
        "ENCRYPTION_KEY",
        "MASTER_KEY",
        "SESSION_KEY",
        "BEARER",
        "AUTHORIZATION",
    )
    if any(kw in upper for kw in sensitive_keywords):
        return True
    # Short names (≤4 chars) that are fully uppercase are likely sensitive
    if len(name) <= 4 and name.isupper() and name.isalpha():
        return True
    return False


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a ``.env`` file and return ``{key: value}`` pairs.

    Supports:
    - ``KEY=value`` and ``KEY="value"`` and ``KEY='value'``
    - ``export KEY=value`` prefix
    - Inline and trailing ``#`` comments
    """

    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Strip leading "export "
        if line.startswith("export "):
            line = line[7:]
        # Split on first =
        eq = line.find("=")
        if eq <= 0:
            continue
        key = line[:eq].strip()
        value = line[eq + 1 :].strip()
        # Strip quotes and trailing comments
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        else:
            comment = value.find(" #")
            if comment > 0:
                value = value[:comment]
        result[key] = value
    return result


def scan_env_file(path: Path, store: "SecretStore") -> int:
    """Scan *path* for sensitive env vars and add their values to *store*.

    Returns the number of new secrets added.
    """

    entries = parse_env_file(path)
    count = 0
    for name, value in entries.items():
        if looks_sensitive_name(name) and value:
            store.add(value)
            count += 1
    return count


class SecretStore:
    """Deterministic secret store for literal-value redaction.

    Manages a set of known literal secrets persisted to
    ``data/private/secrets/known.txt`` and optional env-file scanning
    metadata in ``env.json``.
    """

    def __init__(self, store_dir: Path) -> None:
        """Initialize store from *store_dir*."""

        self._dir = store_dir
        self._known_path = store_dir / _KNOWN_FILE
        self._env_meta_path = store_dir / _ENV_META_FILE
        self._text_secrets: list[str] = []
        self._binary_secrets: list[bytes] = []
        self._dirty = False
        self._reload()

    # ---- persistence ----

    def _reload(self) -> None:
        """Reload secrets from disk."""

        text, binary = _load_known(self._known_path)
        self._text_secrets = _sort_descending(text)
        self._binary_secrets = binary
        self._dirty = False

    def _save(self) -> None:
        """Persist secrets to disk.

        Multiline secrets and secrets starting with ``b64:`` are base64-encoded
        and stored with a ``b64:`` prefix to preserve line-based formatting.
        """

        self._dir.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        for secret in sorted(set(self._text_secrets)):
            if "\n" in secret or secret.startswith(_B64_PREFIX):
                encoded = base64.b64encode(secret.encode("utf-8")).decode("ascii")
                lines.append(f"{_B64_PREFIX}{encoded}")
            else:
                lines.append(secret)
        self._known_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self._dirty = False

    def _ensure_saved(self) -> None:
        """Write to disk if there are pending changes."""

        if self._dirty:
            self._save()

    # ---- public API ----

    @property
    def count(self) -> int:
        """Return the total number of stored secrets."""

        self._ensure_saved()
        return len(self._text_secrets) + len(self._binary_secrets)

    def add(self, secret: str) -> bool:
        """Add a literal *secret* to the store.

        Raises :exc:`ValueError` if *secret* exceeds ``_MAX_SECRET_SIZE``.
        Returns True if the secret was newly added, False if already present.
        """

        if len(secret.encode("utf-8")) > _MAX_SECRET_SIZE:
            raise ValueError(f"Secret exceeds maximum size of {_MAX_SECRET_SIZE} bytes")
        if secret in self._text_secrets:
            return False
        self._text_secrets.append(secret)
        self._text_secrets = _sort_descending(self._text_secrets)
        self._dirty = True
        self._ensure_saved()
        # Also try as base64 binary
        try:
            decoded = base64.b64decode(secret, validate=True)
            if (
                decoded != secret.encode("utf-8")
                and decoded not in self._binary_secrets
            ):
                self._binary_secrets.append(decoded)
        except ValueError:
            pass
        return True

    def remove(self, secret: str) -> bool:
        """Remove a literal *secret* from the store by value.

        Returns True if the secret was found and removed.
        """

        if secret not in self._text_secrets:
            return False
        self._text_secrets = [s for s in self._text_secrets if s != secret]
        self._dirty = True
        self._ensure_saved()
        return True

    def remove_by_hash(self, hash_prefix: str) -> bool:
        """Remove a secret whose hash starts with *hash_prefix*.

        Returns True if exactly one match was found and removed.
        """

        matches = [
            s
            for s in self._text_secrets
            if hash_bytes(s.encode("utf-8")).startswith(hash_prefix)
        ]
        if len(matches) != 1:
            return False
        return self.remove(matches[0])

    def list_secrets(self) -> list[tuple[str, str, str]]:
        """Return ``(hash_prefix, masked_value, raw_value)`` for all text secrets.

        The masked value shows the first 4 and last 4 characters of the secret.
        Raw values longer than 80 characters are truncated for display.
        """

        self._ensure_saved()
        results: list[tuple[str, str, str]] = []
        for secret in self._text_secrets:
            h = hash_bytes(secret.encode("utf-8"))[:12]
            masked = (
                secret[:4] + "*" * min(8, len(secret) - 8) + secret[-4:]
                if len(secret) > 8
                else secret
            )
            raw = secret[:40] + "..." + secret[-40:] if len(secret) > 80 else secret
            results.append((h, masked, raw))
        return results

    def compute_hash(self) -> str:
        """Compute a deterministic hash over all stored secrets."""

        self._ensure_saved()
        # Sort for determinism
        combined = "\n".join(sorted(set(self._text_secrets))) + "\n"
        return hash_bytes(combined.encode("utf-8"))

    def replace_all(self, text: str) -> str:
        """Replace all known secrets in *text* with redacted markers.

        Text secrets are tried first (longest-first), then binary secrets
        (base64-encoded form). Both phases are skipped if *text* is empty.
        """

        if not text:
            return text
        text = _replace_literals(text, self._text_secrets)
        text = _replace_binary(text, self._binary_secrets)
        return text

    # ---- env-file scanning ----

    def scan_env_file(self, path: Path) -> int:
        """Scan an env file and add sensitive values.

        Returns the number of new secrets added.
        """

        return scan_env_file(path, self)

    def read_env_meta(self) -> dict[str, Any]:
        """Read env-file scanning metadata."""

        if self._env_meta_path.exists():
            return json.loads(self._env_meta_path.read_text(encoding="utf-8"))
        return {}

    def write_env_meta(self, meta: dict[str, Any]) -> None:
        """Write env-file scanning metadata."""

        self._dir.mkdir(parents=True, exist_ok=True)
        self._env_meta_path.write_text(
            json.dumps(meta, indent=2) + "\n", encoding="utf-8"
        )

    def scan_and_record(self, path: Path) -> int:
        """Scan *path*, add secrets, and update metadata.

        Returns the number of new secrets added.
        """

        added = self.scan_env_file(path)
        meta = self.read_env_meta()
        scanned = meta.get("scanned_files", [])
        scanned.append(
            {
                "path": str(path.resolve()),
                "added": added,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        meta["scanned_files"] = scanned
        self.write_env_meta(meta)
        return added
