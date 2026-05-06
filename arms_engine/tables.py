"""Low-level markdown task-table parsing utilities.

This module is intentionally import-free of other arms_engine modules so that
both ``protocols.py`` and ``compression.py`` can import from here without
creating a circular dependency.
"""


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

    existing_normalized_tasks = {normalize_task_text(row["Task"]) for row in existing_rows}

    new_startup_rows = [
        row
        for row in startup_rows
        if normalize_task_text(row["Task"]) not in existing_normalized_tasks
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
