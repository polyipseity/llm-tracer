---
description: "Use when editing pyproject.toml, prek.toml, CI workflows, commitlint config, or dependency automation. Preserves UV-first tooling contracts and lockfile-safe workflows."
name: "UV and Tooling Contracts"
applyTo: "pyproject.toml, prek.toml, opencode.jsonc, .commitlintrc.mjs, .github/workflows/**/*.yml, .github/dependabot.yml"
---

# UV and Tooling Contracts

- Preserve the UV-first workflow. See `AGENTS.md` § **Build and Test** for canonical commands.
- Keep version constraints intentional:
  - `requires-python = ">=3.14.0"`
  - `[tool.uv].required-version = ">=0.11.0"`
- Prefer `uv run --locked ...` for all Python tools (test, lint, format, type-check).
- When changing dependency config, ensure `uv.lock` stays in sync and
  `dependabot.yml` remains accurate.
- Keep `opencode.jsonc` instruction/skill paths valid when moving directories.
- If Bun or other JS orchestration is introduced later, update `AGENTS.md` and
  this instruction intentionally instead of assuming it is always present.
