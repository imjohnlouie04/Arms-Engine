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
