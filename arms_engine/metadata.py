TASK_TABLE_HEADER = "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |"
TASK_TABLE_DIVIDER = "|---|------|----------------|--------------|--------------|--------|"
TASK_TABLE_COLUMNS = "# | Task | Assigned Agent | Active Skill | Dependencies | Status"

SESSION_ENVIRONMENT_KEYS = (
    "ARMS Root",
    "Engine Version",
    "Project Root",
    "Project Name",
    "Execution Mode",
    "YOLO Mode",
)
SESSION_BOOTSTRAP_HEADINGS = (
    "Environment",
    "Active Agents",
    "Active Skills",
    "Memory Signals",
    "Memory Packet",
    "Memory Suggestions",
    "Next Recommended Step",
    "Active Tasks",
    "Completed Tasks",
    "Blockers",
)

PROTOCOL_REPORT_PREFIXES = ("review", "fix-plan", "release-notes", "release-check")
REPORT_HISTORY_FILENAME = "REPORT_HISTORY.md"
REPORT_HISTORY_HEADER = """# ARMS Report History

> Consolidated by ARMS. Older protocol report revisions are appended here while the latest revision stays in its stable `*-latest.md` file.
"""


def render_empty_task_table():
    return "{}\n{}".format(TASK_TABLE_HEADER, TASK_TABLE_DIVIDER)


def latest_report_filename(prefix):
    return "{}-latest.md".format(prefix)


def is_latest_report_filename(name):
    return name.endswith("-latest.md")
