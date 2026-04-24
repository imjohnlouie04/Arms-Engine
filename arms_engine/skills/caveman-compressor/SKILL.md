# SKILL: Caveman Compressor (Context Optimization)
**ID:** `caveman-compressor`
**Role:** Context Efficiency Specialist.

## Purpose
Shrink `SESSION.md` and `MEMORY.md` into high-density, token-efficient formats without losing technical requirements or architectural decisions.

## Activation
Triggered by `arms init compress` or explicitly via `/agent arms-main-agent @caveman-compressor`.

## Procedures

### 1. SESSION.md Compression
- Move all tasks marked **Done** or **Cancelled** to `./.gemini/SESSION_ARCHIVE.md`.
- Group remaining **Active Tasks** by priority.
- Prune redundant status updates while keeping the final state.
- Ensure the **Strategic Task Table** remains valid Markdown.

### 2. MEMORY.md Summarization
- Use "Caveman Style" (high-density noun-heavy phrases).
- Remove conversational filler and reasoning.
- Keep ONLY:
    - Decisions made.
    - Path resolutions.
    - Error patterns and fixes.
    - User preferences.
- Format: `[TOPIC] : ACTION -> RESULT`

### 3. Archive Maintenance
- Append to `SESSION_ARCHIVE.md` instead of overwriting.
- If the archive exceeds 20k tokens, summarize the oldest entries into a `HISTORY_SUMMARY.md`.

## Quality Gate
- A "Compressed" file MUST still be human-readable and agent-executable.
- Never delete `Pending` tasks.
- Never delete `Blocked` tasks without a resolution note.
