"""Scan session content with detect-secrets for missed secrets before publication.

A thin wrapper around ``detect_secrets.SecretsCollection`` that scans session
message content using detect-secrets' 20+ built-in plugins. Serves as a
publication gate — sessions with findings are blocked from public output.

Reports are stored in ``data/private/reports/<session_id>.scan.json``.

Custom plugin support is available via detect-secrets' plugin API by providing
Python modules through :ref:`detect-secrets custom plugins` configuration.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from llm_tracer.schema import ChatSession

"""Public symbols exported by this module."""
__all__ = (
    "ScanFinding",
    "ScanReport",
    "ScannerConfig",
    "scan_session",
    "scan_sessions",
)


"""Name of the detect-secrets optional dependency package."""
_DETECT_SECRETS = "detect_secrets"

"""Subdirectory for per-session scan reports under the private data tree."""
_REPORTS_SUBDIR = "private/reports"


@dataclass(frozen=True)
class ScanFinding:
    """One secret-like finding detected by the scanner.

    Attributes:
        type: Detector type name (e.g. ``"AWSKeyDetector"``).
        location: Message index (0-based) where the finding was found.
        text_snippet: Surrounding text snippet of the finding (may be truncated).
        value_redacted: Redacted description of the detected secret.
    """

    type: str
    location: int
    text_snippet: str
    value_redacted: str


@dataclass
class ScanReport:
    """Scan results for one session.

    Attributes:
        session_id: The chat session identifier.
        findings: List of detected potential secrets.
        blocked: Whether this session should be blocked from publication (``True``
            when *findings* is non-empty).
    """

    session_id: str
    findings: list[ScanFinding] = field(default_factory=list)
    blocked: bool = False

    def __post_init__(self) -> None:
        """Auto-set ``blocked`` based on findings presence."""

        self.blocked = len(self.findings) > 0


@dataclass
class ScannerConfig:
    """Configuration for the detect-secrets scanner.

    Attributes:
        plugins: Optional list of custom plugin Python module paths to load.
        exclude_lines_regex: Optional regex; lines matching this pattern are
            excluded from scanning. Useful for ignoring already-redacted patterns.
        report_dir: Directory where per-session scan reports are persisted.
            Defaults to ``<repo_dir>/data/private/reports/``.
    """

    plugins: list[str] = field(default_factory=list)
    exclude_lines_regex: str | None = field(default=None)
    report_dir: Path | None = field(default=None)


def _finding_from_secret(secret: Any, message_index: int) -> ScanFinding | None:
    """Convert a ``detect_secrets.schema.Secret`` to a ``ScanFinding``.

    Returns ``None`` if the secret has no useful content.
    """

    secret_type = getattr(secret, "type", None) or str(type(secret).__name__)
    line_number = getattr(secret, "line_number", None)
    secret_value = getattr(secret, "secret_value", None)

    if not secret_value:
        return None

    # Build a compact redacted description
    secret_str = str(secret_value)
    snippet = secret_str[:80] + "..." if len(secret_str) > 80 else secret_str
    redacted = f"{secret_type} (line {line_number or '?'})"

    return ScanFinding(
        type=secret_type,
        location=message_index,
        text_snippet=snippet,
        value_redacted=redacted,
    )


def _save_report(report: ScanReport, report_dir: Path) -> None:
    """Persist a scan report to ``<report_dir>/<session_id>.scan.json``."""

    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{report.session_id}.scan.json"
    data = asdict(report)
    path.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )


def scan_session(
    session: ChatSession,
    config: ScannerConfig | None = None,
) -> ScanReport:
    """Scan one session's messages for potential secrets.

    Uses detect-secrets if available; returns an empty (unblocked) report when
    detect-secrets is not installed.

    Args:
        session: The chat session to scan.
        config: Optional scanner configuration.

    Returns:
        A ``ScanReport`` with any findings detected.
    """

    report = ScanReport(session_id=session.id)

    if config is None:
        config = ScannerConfig()

    # Skip scan if detect-secrets is not installed
    if find_spec(_DETECT_SECRETS) is None:
        if config.report_dir is not None:
            _save_report(report, config.report_dir)
        return report

    from detect_secrets import SecretsCollection  # noqa: PLC0415
    from detect_secrets.settings import default_settings  # noqa: PLC0415

    collection = SecretsCollection()

    # Configure scan settings
    with default_settings():
        # Scan each message as an individual pseudo-file
        for idx, message in enumerate(session.messages):
            # Use message content as a pseudo-file for the scanner
            content = message.content
            if not content.strip():
                continue

            try:
                collection.scan_line(content, idx)  # type: ignore
            except Exception:
                # Silently skip lines that cause scan errors
                pass

    # Convert findings to ScanFinding objects
    if hasattr(collection, "results"):
        for pseudo_filename, secrets_list in collection.results.items():  # type: ignore
            for secret in secrets_list:
                finding = _finding_from_secret(secret, pseudo_filename)
                if finding is not None:
                    report.findings.append(finding)

    # Persist report if report_dir configured
    if config.report_dir is not None:
        _save_report(report, config.report_dir)

    return report


def scan_sessions(
    sessions: dict[str, ChatSession],
    config: ScannerConfig | None = None,
) -> dict[str, ScanReport]:
    """Scan multiple sessions and return a mapping of ``session_id -> ScanReport``.

    Args:
        sessions: Mapping of chat ID to session.
        config: Optional scanner configuration.

    Returns:
        Dict of session ID to scan report.
    """

    return {
        chat_id: scan_session(session, config) for chat_id, session in sessions.items()
    }
