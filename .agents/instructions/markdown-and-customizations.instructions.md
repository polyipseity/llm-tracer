---
description: "Use when editing markdown documentation, prompts, or instruction files. Covers markdownlint-aware style, concise linking strategy, and safe customization frontmatter practices."
name: "Markdown and Customization Authoring"
applyTo: "**/*.md"
---

# Markdown and Customization Authoring

- Keep markdown concise, scannable, and task-oriented.
- Follow `.markdownlint.jsonc` (and `.agents/.markdownlint.jsonc` for `.agents/**`).
- Prefer links to canonical policy (`AGENTS.md`) over repeated rule text.
- For `.instructions.md` files:
  - Include YAML frontmatter with keyword-rich `description` starting with
    "Use when".
  - Keep `applyTo` globs narrow to avoid unnecessary context load.
  - Keep one primary concern per file and link related guidance.
- Keep `AGENTS.md` short; move niche guidance into
  `.agents/instructions/*.instructions.md`.
