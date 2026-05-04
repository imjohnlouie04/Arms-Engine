"""Centralised token budgets and compaction limits for the ARMS workspace.

All modules should import from here instead of defining their own constants.
Limits can be tuned via environment variables for power users without code changes.
"""

import os


def _int_env(name: str, default: int) -> int:
    """Read an integer from an env var, falling back to *default* on parse errors."""
    raw = os.environ.get(name, "")
    if raw.strip().isdigit():
        return int(raw.strip())
    return default


# ── SESSION.md token budget ──────────────────────────────────────────────────
# Arms doctor warns when SESSION.md exceeds this many estimated tokens.
SESSION_TOKEN_BUDGET: int = _int_env("ARMS_SESSION_TOKEN_BUDGET", 2000)

# Ratio of budget at which the "approaching limit" warning fires (0–1).
DEFAULT_TOKEN_BUDGET_WARN_RATIO: float = 0.9

# ── CONTEXT_SYNTHESIS.md / GENERATED_PROMPTS.md budgets ─────────────────────
CONTEXT_SYNTHESIS_TOKEN_BUDGET: int = _int_env("ARMS_CONTEXT_SYNTHESIS_TOKEN_BUDGET", 2200)
GENERATED_PROMPTS_TOKEN_BUDGET: int = _int_env("ARMS_GENERATED_PROMPTS_TOKEN_BUDGET", 1600)

# ── arms init compress limits ─────────────────────────────────────────────────
# Maximum chars in SESSION.md / MEMORY.md before auto-compact triggers.
AUTO_COMPACT_SESSION_CHAR_LIMIT: int = _int_env("ARMS_AUTO_COMPACT_SESSION_CHAR_LIMIT", 12000)
AUTO_COMPACT_MEMORY_CHAR_LIMIT: int = _int_env("ARMS_AUTO_COMPACT_MEMORY_CHAR_LIMIT", 12000)

# Maximum number of report files kept in .arms/reports/ before oldest are pruned.
AUTO_COMPACT_REPORT_FILE_LIMIT: int = _int_env("ARMS_AUTO_COMPACT_REPORT_FILE_LIMIT", 12)

# Maximum number of agent output files kept in .arms/agent-outputs/.
AUTO_COMPACT_AGENT_OUTPUT_FILE_LIMIT: int = _int_env("ARMS_AUTO_COMPACT_AGENT_OUTPUT_FILE_LIMIT", 20)

# Maximum chars in SESSION_ARCHIVE.md before compression is recommended.
ARCHIVE_TOKEN_LIMIT: int = _int_env("ARMS_ARCHIVE_TOKEN_LIMIT", 20000)

# ── watch mode ───────────────────────────────────────────────────────────────
WATCH_POLL_INTERVAL_SECONDS: float = float(
    os.environ.get("ARMS_WATCH_POLL_INTERVAL_SECONDS", "2.0")
)
