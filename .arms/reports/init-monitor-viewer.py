import json
import os
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
