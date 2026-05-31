---
description: "Use when adding or editing files under scripts/. Covers executable-bit expectations, cross-platform line endings, and script placement rules enforced by tests."
name: "Scripts and Executable Permissions"
applyTo: "scripts/*.sh, scripts/*.py, scripts/*.ps1, scripts/*.bat, scripts/*.cmd"
---

# Scripts and Executable Permissions

- Keep top-level scripts in `scripts/` unless tests are updated.
- Respect line endings:
  - `.sh` uses LF
  - `.ps1`, `.bat` use CRLF
- On non-Windows platforms, ensure executable scripts have executable bits set
  (enforced by `tests/test_git_executable.py`).
- Prefer portable script behavior and avoid shell-specific assumptions unless
  the extension constrains the shell.
- If introducing new script extensions or locations, update tests and globs intentionally.
