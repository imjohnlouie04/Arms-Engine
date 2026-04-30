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
- Read `.arms/SESSION.md`, `.arms/BRAND.md`, and `.arms/MEMORY.md` before any task work.
- Treat `## Memory Signals` in `.arms/SESSION.md` as hot context, then open `.arms/MEMORY.md` when the work touches prior lessons, preferences, or known bugs.
- Ask the user for approval before updating `.arms/MEMORY.md`; only append after approval, and never overwrite it wholesale.
- After significant work, draft a concise memory lesson candidate and ask for approval before appending it to `.arms/MEMORY.md`.
- Keep `.arms/SESSION.md` synchronized with task progress and blockers.
