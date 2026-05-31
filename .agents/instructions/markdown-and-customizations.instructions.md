---
description: "Use when editing markdown documentation, prompts, or instruction files. Covers markdownlint-aware style, concise linking strategy, and safe customization frontmatter practices."
name: "Markdown and Customization Authoring"
applyTo: "**/*.md"
---

# Markdown and Customization Authoring

- Keep markdown concise, scannable, and task-oriented.
- Follow `.markdownlint.jsonc` (and `.agents/.markdownlint.jsonc` for `.agents/**`).
- Link to canonical files instead of duplicating long content.
- For `.instructions.md` files:
  - Include YAML frontmatter with keyword-rich `description` ("Use when...").
  - Use narrow `applyTo` globs to avoid unnecessary context load.
  - Keep one primary concern per file; link to related guidance.
- For `AGENTS.md` and root docs: Keep short; extract specialized guidance to
  `.agents/instructions/` files and link back.
