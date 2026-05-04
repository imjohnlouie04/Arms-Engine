"""Standalone terminal HUD viewer for arms init --monitor.

This script is written to disk by InitMonitor._write_viewer_script() and run in
a separate terminal window.  It reads a JSON snapshot file written by the ARMS
engine and re-renders a live ASCII dashboard every 0.5 seconds.

It must have **no** runtime dependencies on the arms_engine package; all helpers
are self-contained.
"""

import json
import os
import re
import shutil
import sys
import time

TERMINAL_WIDTH = 100
STATUS_LABELS = {
    "idle": "Idle",
    "running": "Running",
    "complete": "Complete",
    "awaiting_input": "Awaiting Input",
    "failed": "Failed",
}
STEP_STATUS_LABELS = {
    "running": "Running",
    "done": "Done",
    "failed": "Failed",
}
PLACEHOLDER_BRAND_TOKENS = (
    "[Name]",
    "[Purpose]",
    "[Long-term goal]",
    "[Voice/Tone]",
    "1. Primary use case:",
    "> New project detected.",
)


def truncate_text(text, width):
    text = str(text)
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width == 1:
        return text[:1]
    return text[: width - 1] + "..."


def pad_line(text, width):
    clipped = truncate_text(text, width)
    return clipped + (" " * max(width - len(clipped), 0))


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            return handle.read()
    except FileNotFoundError:
        return ""


def format_timestamp(timestamp):
    if not timestamp:
        return "Not yet"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


def extract_section(content, title):
    marker = "## " + title
    start = content.find(marker)
    if start == -1:
        return ""
    remainder = content[start + len(marker):]
    if remainder.startswith("\n"):
        remainder = remainder[1:]
    next_index = remainder.find("\n## ")
    if next_index == -1:
        return remainder.strip()
    return remainder[:next_index].strip()


def extract_environment_value(content, label):
    pattern = r"^- " + re.escape(label) + r":\s*(.+)$"
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        return "Unknown"
    return match.group(1).strip()


def parse_task_rows(content):
    rows = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 6:
            continue
        first_cell = cells[0].replace(" ", "")
        if cells[0] == "#" or set(first_cell) <= {"-"}:
            continue
        rows.append(
            {
                "task": cells[1],
                "status": cells[5],
            }
        )
    return rows


def _arms_path(project_root, filename):
    return os.path.join(project_root, ".arms", filename)


def summarize_workspace(project_root):
    session_path = _arms_path(project_root, "SESSION.md")
    brand_path = _arms_path(project_root, "BRAND.md")
    context_path = _arms_path(project_root, "CONTEXT_SYNTHESIS.md")
    prompts_path = _arms_path(project_root, "GENERATED_PROMPTS.md")
    memory_path = _arms_path(project_root, "MEMORY.md")

    session_content = read_text(session_path)
    environment = extract_section(session_content, "Environment")
    active_tasks = extract_section(session_content, "Active Tasks")
    blockers_body = extract_section(session_content, "Blockers")
    task_rows = parse_task_rows(active_tasks)

    counts = {"pending": 0, "in_progress": 0, "blocked": 0, "other": 0}
    live_tasks = []
    for row in task_rows:
        normalized = row["status"].strip().lower()
        if normalized in {"pending"}:
            counts["pending"] += 1
        elif normalized in {"in progress", "pre-flight"}:
            counts["in_progress"] += 1
        elif normalized in {"blocked", "failed"}:
            counts["blocked"] += 1
        else:
            counts["other"] += 1
        if normalized not in {"done", "cancelled", "canceled"} and len(live_tasks) < 5:
            live_tasks.append("[{}] {}".format(row["status"].upper(), row["task"]))

    blockers = []
    for raw_line in blockers_body.splitlines():
        cleaned = raw_line.strip()
        if not cleaned:
            continue
        if cleaned.startswith("- "):
            cleaned = cleaned[2:].strip()
        blockers.append(cleaned)
    if not blockers:
        blockers = ["None"]

    brand_content = read_text(brand_path)
    brand_ready = bool(brand_content.strip()) and not any(
        token in brand_content for token in PLACEHOLDER_BRAND_TOKENS
    )

    return {
        "session_status": "Present" if session_content.strip() else "Missing",
        "session_updated": format_timestamp(os.path.getmtime(session_path)) if os.path.exists(session_path) else "Not yet",
        "execution_mode": extract_environment_value(environment, "Execution Mode"),
        "yolo_mode": extract_environment_value(environment, "YOLO Mode"),
        "brand_status": "Ready" if brand_ready else "Waiting",
        "context_status": "Present" if os.path.exists(context_path) else "Missing",
        "prompts_status": "Present" if os.path.exists(prompts_path) else "Missing",
        "memory_status": "Present" if os.path.exists(memory_path) else "Missing",
        "task_summary": "{total} total | {active} active | {blocked} blocked | {pending} pending".format(
            total=len(task_rows),
            active=counts["in_progress"],
            blocked=counts["blocked"],
            pending=counts["pending"],
        ),
        "blockers": blockers[:3],
        "live_tasks": live_tasks or ["No active tasks."],
    }


def render_terminal_dashboard(snapshot, width=TERMINAL_WIDTH):
    inner_width = max(width - 4, 40)
    top = "+" + ("-" * (inner_width + 2)) + "+"
    lines = [top]
    header = " ARMS INIT HUD "
    status = STATUS_LABELS.get(snapshot.get("status"), "Unknown").upper()
    status_text = "[{}]".format(status)
    header_width = max(inner_width - len(status_text) - 1, 0)
    lines.append("| {} {} |".format(pad_line(header, header_width), pad_line(status_text, len(status_text))))
    lines.append("| {} |".format(pad_line("", inner_width)))
    details = [
        "Command: {} | Mode: {} | Engine: {}".format(
            snapshot.get("command", "init"),
            "YOLO" if snapshot.get("is_yolo") else "Standard",
            snapshot.get("engine_version", "unknown"),
        ),
        "Project: {}".format(snapshot.get("project_root", "Unknown")),
        "ARMS Root: {}".format(snapshot.get("arms_root", "Pending")),
        "Report : {}".format(snapshot.get("report_path", "Pending")),
        "Updated: {}".format(snapshot.get("updated_at", "Not yet")),
        "Summary: {}".format(snapshot.get("summary", "Waiting to start.")),
    ]
    if snapshot.get("error_message"):
        details.append("Error  : {}".format(snapshot["error_message"]))
    for detail in details:
        lines.append("| {} |".format(pad_line(detail, inner_width)))
    workspace = summarize_workspace(snapshot.get("project_root", ""))
    lines.append("| {} |".format(pad_line("", inner_width)))
    lines.append("| {} |".format(pad_line("Workspace", inner_width)))
    lines.append("| {} |".format(pad_line("-" * min(inner_width, 24), inner_width)))
    lines.append("| {} |".format(pad_line("Session : {} ({})".format(workspace["session_status"], workspace["session_updated"]), inner_width)))
    lines.append("| {} |".format(pad_line("Mode    : {} | YOLO: {}".format(workspace["execution_mode"], workspace["yolo_mode"]), inner_width)))
    lines.append("| {} |".format(pad_line("Files   : BRAND={} | CONTEXT={} | PROMPTS={} | MEMORY={}".format(workspace["brand_status"], workspace["context_status"], workspace["prompts_status"], workspace["memory_status"]), inner_width)))
    lines.append("| {} |".format(pad_line("Tasks   : {}".format(workspace["task_summary"]), inner_width)))
    lines.append("| {} |".format(pad_line("Blockers: {}".format(" | ".join(workspace["blockers"])), inner_width)))
    lines.append("| {} |".format(pad_line("", inner_width)))
    lines.append("| {} |".format(pad_line("Live Tasks", inner_width)))
    lines.append("| {} |".format(pad_line("-" * min(inner_width, 24), inner_width)))
    for task in workspace["live_tasks"]:
        lines.append("| {} |".format(pad_line(task, inner_width)))
    lines.append("| {} |".format(pad_line("", inner_width)))
    lines.append("| {} |".format(pad_line("Steps", inner_width)))
    lines.append("| {} |".format(pad_line("-" * min(inner_width, 24), inner_width)))

    steps = snapshot.get("steps", [])
    if not steps:
        lines.append("| {} |".format(pad_line("No init steps recorded yet.", inner_width)))
    else:
        for step in steps[-10:]:
            status_label = STEP_STATUS_LABELS.get(step.get("status"), "Unknown").upper()
            prefix = "[{}] {:02d}".format(status_label, int(step.get("index", 0)))
            detail = "{} {} ({})".format(prefix, step.get("label", ""), step.get("duration", "0.0s"))
            lines.append("| {} |".format(pad_line(detail, inner_width)))
            if step.get("details"):
                lines.append("| {} |".format(pad_line("  " + step["details"], inner_width)))

    lines.append("| {} |".format(pad_line("", inner_width)))
    footer = "Press Ctrl+C or close this window when done."
    if snapshot.get("status") == "awaiting_input":
        footer = "Init is waiting on input. Leave this HUD open while you work."
    lines.append("| {} |".format(pad_line(footer, inner_width)))
    lines.append(top)
    return "\n".join(lines)


def main():
    snapshot_file = os.path.abspath(sys.argv[1])
    while True:
        try:
            with open(snapshot_file, "r", encoding="utf-8") as f:
                snapshot = json.load(f)
        except FileNotFoundError:
            snapshot = {
                "status": "failed",
                "summary": "Snapshot file not found.",
                "steps": [],
                "project_root": os.path.dirname(os.path.dirname(snapshot_file)),
                "report_path": snapshot_file,
                "updated_at": "Not yet",
                "engine_version": "unknown",
            }
        os.system("clear")
        print(render_terminal_dashboard(snapshot, width=shutil.get_terminal_size((TERMINAL_WIDTH, 30)).columns))
        time.sleep(0.5)


if __name__ == "__main__":
    main()
