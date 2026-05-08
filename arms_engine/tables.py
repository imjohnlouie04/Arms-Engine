"""Low-level markdown task-table parsing utilities.

This module is intentionally import-free of other arms_engine modules so that
both ``protocols.py`` and ``compression.py`` can import from here without
creating a circular dependency.
"""

import re


TOKEN_RE = re.compile(r"[a-z0-9]+")
PHASE_PREFIX_RE = re.compile(r"^[a-z][a-z0-9_-]*:\s*", re.IGNORECASE)
TASK_MATCH_STOPWORDS = {
    "a",
    "an",
    "and",
    "before",
    "current",
    "existing",
    "first",
    "for",
    "high",
    "impact",
    "immediate",
    "in",
    "latest",
    "new",
    "of",
    "on",
    "the",
    "to",
    "with",
}


def parse_task_rows(content):
    """Parse a markdown task table and return a list of 6-field row dicts.

    Each returned dict has keys: ``#``, ``Task``, ``Assigned Agent``,
    ``Active Skill``, ``Dependencies``, ``Status``.

    The ``&#124;`` HTML entity is unescaped back to a literal ``|`` so that
    pipe characters inside task descriptions survive the round-trip through
    ``render_task_table``.
    """
    rows = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [cell.strip().replace("&#124;", "|") for cell in line.strip("|").split("|")]
        if len(cells) != 6:
            continue
        first_cell = cells[0].replace(" ", "")
        if cells[0] == "#" or set(first_cell) <= {"-"}:
            continue
        rows.append(
            {
                "#": cells[0],
                "Task": cells[1],
                "Assigned Agent": cells[2],
                "Active Skill": cells[3],
                "Dependencies": cells[4],
                "Status": cells[5],
            }
        )
    return rows


def normalize_task_text(task_text):
    """Normalize task text for deduplication comparison (lowercase, single spaces)."""
    return " ".join((task_text or "").split()).strip().casefold()


def _normalize_token(token):
    normalized = (token or "").strip().casefold()
    if len(normalized) > 4 and normalized.endswith("ies"):
        return normalized[:-3] + "y"
    if len(normalized) > 4 and normalized.endswith("es"):
        return normalized[:-2]
    if len(normalized) > 4 and normalized.endswith("s"):
        return normalized[:-1]
    return normalized


def informative_task_tokens(task_text):
    """Return stable comparison tokens for a task description."""
    stripped = PHASE_PREFIX_RE.sub("", task_text or "").casefold()
    tokens = []
    for raw_token in TOKEN_RE.findall(stripped):
        token = _normalize_token(raw_token)
        if not token or token in TASK_MATCH_STOPWORDS:
            continue
        tokens.append(token)
    return tuple(tokens)


def task_text_similarity(task_a, task_b):
    """Return a coarse similarity score for two task descriptions."""
    normalized_a = normalize_task_text(task_a)
    normalized_b = normalize_task_text(task_b)
    if normalized_a == normalized_b:
        return 1.0

    tokens_a = set(informative_task_tokens(task_a))
    tokens_b = set(informative_task_tokens(task_b))
    if not tokens_a or not tokens_b:
        return 0.0

    overlap = len(tokens_a & tokens_b)
    return overlap / max(len(tokens_a), len(tokens_b))


def task_rows_semantically_match(row_a, row_b):
    """Return True when two rows likely describe the same work item."""
    agent_a = (row_a.get("Assigned Agent", "") or "").strip().casefold()
    agent_b = (row_b.get("Assigned Agent", "") or "").strip().casefold()
    if agent_a and agent_b and agent_a != agent_b:
        return False
    return task_text_similarity(row_a.get("Task", ""), row_b.get("Task", "")) >= 0.75


def best_semantic_row_match(candidate_row, existing_rows, used_indexes=None):
    """Find the strongest semantic match for *candidate_row* in *existing_rows*."""
    used_indexes = used_indexes or set()
    best_index = None
    best_score = 0.0
    for index, row in enumerate(existing_rows):
        if index in used_indexes:
            continue
        if not task_rows_semantically_match(candidate_row, row):
            continue
        score = task_text_similarity(candidate_row.get("Task", ""), row.get("Task", ""))
        if score > best_score:
            best_index = index
            best_score = score
    if best_index is None:
        return None
    return best_index, existing_rows[best_index]


def deduplicate_startup_tasks_against_existing(startup_tasks_content, existing_session_content):
    """Merge startup tasks into existing SESSION.md, skipping duplicates.

    If a task with the same normalized text already exists in the existing
    session, it is NOT duplicated. Only truly new tasks are added.

    Args:
        startup_tasks_content: Markdown table of startup tasks to add.
        existing_session_content: Full SESSION.md content.

    Returns:
        Updated startup_tasks_content with duplicates removed, or original
        if no existing session tasks are found.
    """
    if not startup_tasks_content or not existing_session_content:
        return startup_tasks_content

    startup_rows = parse_task_rows(startup_tasks_content)
    existing_rows = parse_task_rows(existing_session_content)

    if not startup_rows or not existing_rows:
        return startup_tasks_content

    new_startup_rows = [
        row
        for row in startup_rows
        if best_semantic_row_match(row, existing_rows) is None
    ]

    if not new_startup_rows:
        return ""

    if len(new_startup_rows) == len(startup_rows):
        return startup_tasks_content

    lines = [
        "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |",
        "|---|------|----------------|--------------|--------------|--------|",
    ]
    for index, row in enumerate(new_startup_rows, start=1):
        lines.append(
            f"| {index} | {row['Task']} | {row['Assigned Agent']} | {row['Active Skill']} | {row['Dependencies']} | {row['Status']} |"
        )
    return "\n".join(lines)


def merge_task_tables(existing_table, new_table):
    """Merge new task rows into an existing task table, renumbering as needed.

    Args:
        existing_table: Markdown table of existing tasks.
        new_table: Markdown table of new tasks to add.

    Returns:
        Merged table with all tasks, renumbered sequentially.
    """
    if not new_table:
        return existing_table
    if not existing_table:
        return new_table

    existing_rows = parse_task_rows(existing_table)
    new_rows = parse_task_rows(new_table)

    if not new_rows:
        return existing_table

    merged = existing_rows + new_rows
    lines = [
        "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |",
        "|---|------|----------------|--------------|--------------|--------|",
    ]
    for index, row in enumerate(merged, start=1):
        lines.append(
            f"| {index} | {row['Task']} | {row['Assigned Agent']} | {row['Active Skill']} | {row['Dependencies']} | {row['Status']} |"
        )
    return "\n".join(lines)
