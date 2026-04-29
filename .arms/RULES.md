# ARMS Project Rules

> Managed by ARMS Engine. Replace these defaults with project-specific rules as the workspace matures.

## Structure & Naming
- Follow the existing project structure and naming conventions before introducing new patterns.
- Prefer feature- or domain-based organization over one-off utility sprawl.

## Code Quality
- Keep changes precise, type-safe, and explicit.
- Reuse existing helpers and conventions before adding new abstractions.
- Surface errors clearly; avoid silent fallbacks.

## Validation
- Use the project's existing build, lint, and test commands.
- Run the relevant validation before marking work complete.

## Agent Protocol
- Read `.arms/SESSION.md`, `.arms/BRAND.md`, and `.gemini/MEMORY.md` before major changes.
- Append new project knowledge to `.gemini/MEMORY.md`; never overwrite it wholesale.
- Keep `.arms/SESSION.md` synchronized with task progress and blockers.
