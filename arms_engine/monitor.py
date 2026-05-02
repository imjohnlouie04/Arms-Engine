import datetime
import html
import os
import time
import webbrowser
from pathlib import Path

from . import __version__


STATUS_LABELS = {
    "idle": "Idle",
    "running": "Running",
    "complete": "Complete",
    "awaiting_input": "Awaiting Input",
    "failed": "Failed",
}
STATUS_COLORS = {
    "idle": "#6b7280",
    "running": "#2563eb",
    "complete": "#16a34a",
    "awaiting_input": "#d97706",
    "failed": "#dc2626",
}
STEP_STATUS_LABELS = {
    "running": "Running",
    "done": "Done",
    "failed": "Failed",
}
STEP_STATUS_COLORS = {
    "running": "#2563eb",
    "done": "#16a34a",
    "failed": "#dc2626",
}


def format_duration(started_at, finished_at=None):
    if not started_at:
        return "0.0s"
    if finished_at is None:
        finished_at = time.time()
    return "{:.1f}s".format(max(finished_at - started_at, 0.0))


def format_timestamp(timestamp):
    if not timestamp:
        return "Not yet"
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def summarize_exception(exc):
    exc_name = exc.__class__.__name__
    message = str(exc).strip()
    if not message:
        return exc_name
    return "{}: {}".format(exc_name, message)


class InitActivityMonitor:
    def __init__(self, project_root):
        self.project_root = os.path.abspath(project_root)
        self.report_path = os.path.join(self.project_root, ".arms", "reports", "init-monitor-latest.html")
        self.command = "init"
        self.arms_root = ""
        self.is_yolo = False
        self.run_count = 0
        self.status = "idle"
        self.summary = "Waiting to start."
        self.started_at = None
        self.updated_at = None
        self.error_message = ""
        self.steps = []
        self._opened = False

    def prepare(self):
        os.makedirs(os.path.dirname(self.report_path), exist_ok=True)
        self._write_report()

    def report_uri(self):
        return Path(self.report_path).resolve().as_uri()

    def launch(self):
        self.prepare()
        if self._opened:
            return
        webbrowser.open(self.report_uri(), new=1)
        self._opened = True

    def begin_run(self, arms_root, command, is_yolo):
        self.prepare()
        self.run_count += 1
        self.command = command or "init"
        self.arms_root = os.path.abspath(arms_root)
        self.is_yolo = bool(is_yolo)
        self.status = "running"
        self.summary = "Initializing workspace."
        self.started_at = time.time()
        self.updated_at = self.started_at
        self.error_message = ""
        self.steps = []
        self._write_report()

    def run_step(self, label, func, *args, **kwargs):
        step = {
            "label": label,
            "status": "running",
            "started_at": time.time(),
            "finished_at": None,
            "details": "",
        }
        self.steps.append(step)
        self.summary = "Running {}.".format(label.lower())
        self._write_report()
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            step["status"] = "failed"
            step["finished_at"] = time.time()
            step["details"] = summarize_exception(exc)
            self.status = "failed"
            self.summary = "Failed during {}.".format(label.lower())
            self.error_message = summarize_exception(exc)
            self._write_report()
            raise
        step["status"] = "done"
        step["finished_at"] = time.time()
        self.summary = "Completed {}.".format(label.lower())
        self._write_report()
        return result

    def finish(self, status, summary=""):
        normalized = status or "complete"
        self.status = normalized
        self.summary = summary or STATUS_LABELS.get(normalized, normalized.title())
        self.updated_at = time.time()
        self._write_report()

    def _write_report(self):
        self.updated_at = time.time()
        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write(self._render_report())

    def _render_report(self):
        refresh = ""
        if self.status in {"running", "awaiting_input"}:
            refresh = '<meta http-equiv="refresh" content="1" />'

        steps_markup = []
        if not self.steps:
            steps_markup.append(
                """
                <div class="empty-state">
                  <strong>No init steps recorded yet.</strong>
                  <p>The HUD will start updating as soon as ARMS begins work.</p>
                </div>
                """
            )
        else:
            for index, step in enumerate(self.steps, start=1):
                status = step["status"]
                badge_color = STEP_STATUS_COLORS.get(status, "#6b7280")
                badge_label = STEP_STATUS_LABELS.get(status, status.title())
                details = ""
                if step["details"]:
                    details = '<p class="step-details">{}</p>'.format(html.escape(step["details"]))
                steps_markup.append(
                    """
                    <div class="step-card">
                      <div class="step-header">
                        <span class="step-index">{index:02d}</span>
                        <div>
                          <h3>{label}</h3>
                          <p>{started} - {duration}</p>
                        </div>
                        <span class="badge" style="background:{badge_color};">{badge_label}</span>
                      </div>
                      {details}
                    </div>
                    """.format(
                        index=index,
                        label=html.escape(step["label"]),
                        started=html.escape(format_timestamp(step["started_at"])),
                        duration=html.escape(format_duration(step["started_at"], step["finished_at"])),
                        badge_color=badge_color,
                        badge_label=html.escape(badge_label),
                        details=details,
                    )
                )

        error_markup = ""
        if self.error_message:
            error_markup = """
            <section class="panel error-panel">
              <h2>Latest Error</h2>
              <pre>{}</pre>
            </section>
            """.format(html.escape(self.error_message))

        return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ARMS Init Activity Monitor</title>
  {refresh}
  <style>
    :root {{
      color-scheme: dark;
      --bg: #07111f;
      --panel: rgba(15, 23, 42, 0.88);
      --border: rgba(148, 163, 184, 0.18);
      --text: #e2e8f0;
      --muted: #94a3b8;
      --accent: {accent};
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(37, 99, 235, 0.22), transparent 30%),
        radial-gradient(circle at top right, rgba(14, 165, 233, 0.18), transparent 25%),
        var(--bg);
      color: var(--text);
    }}
    .shell {{
      width: min(1100px, calc(100vw - 32px));
      margin: 24px auto;
      display: grid;
      gap: 16px;
    }}
    .hero {{
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    }}
    .panel {{
      border: 1px solid var(--border);
      background: var(--panel);
      backdrop-filter: blur(16px);
      border-radius: 18px;
      padding: 20px;
      box-shadow: 0 18px 50px rgba(15, 23, 42, 0.35);
    }}
    .status-pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.72);
      border: 1px solid rgba(148, 163, 184, 0.16);
      color: var(--text);
      font-size: 13px;
      letter-spacing: 0.02em;
    }}
    .status-pill::before {{
      content: "";
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: var(--accent);
      box-shadow: 0 0 16px var(--accent);
    }}
    h1, h2, h3, p {{ margin: 0; }}
    .headline {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 18px;
    }}
    .headline p {{
      color: var(--muted);
      margin-top: 8px;
      line-height: 1.5;
    }}
    .stats {{
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      margin-top: 18px;
    }}
    .stat {{
      padding: 14px;
      border-radius: 14px;
      background: rgba(15, 23, 42, 0.56);
      border: 1px solid rgba(148, 163, 184, 0.12);
    }}
    .stat label {{
      display: block;
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }}
    .stat strong {{
      display: block;
      font-size: 15px;
      line-height: 1.4;
      word-break: break-word;
    }}
    .steps {{
      display: grid;
      gap: 12px;
      margin-top: 16px;
    }}
    .step-card {{
      padding: 16px;
      border-radius: 16px;
      background: rgba(15, 23, 42, 0.58);
      border: 1px solid rgba(148, 163, 184, 0.12);
    }}
    .step-header {{
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 14px;
      align-items: start;
    }}
    .step-index {{
      width: 38px;
      height: 38px;
      border-radius: 12px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: rgba(37, 99, 235, 0.18);
      color: #bfdbfe;
      font-weight: 700;
      letter-spacing: 0.05em;
    }}
    .step-header h3 {{
      font-size: 16px;
      margin-bottom: 4px;
    }}
    .step-header p {{
      color: var(--muted);
      font-size: 13px;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      padding: 7px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: white;
    }}
    .step-details {{
      margin-top: 12px;
      color: #fecaca;
      line-height: 1.5;
    }}
    .empty-state {{
      padding: 24px;
      border-radius: 16px;
      border: 1px dashed rgba(148, 163, 184, 0.24);
      color: var(--muted);
    }}
    .empty-state p {{
      margin-top: 8px;
    }}
    .error-panel pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      color: #fecaca;
      font-family: ui-monospace, SFMono-Regular, SFMono-Regular, Menlo, monospace;
    }}
    @media (max-width: 720px) {{
      .shell {{
        width: min(100vw - 16px, 1100px);
        margin: 12px auto;
      }}
      .panel {{
        padding: 16px;
      }}
      .step-header {{
        grid-template-columns: 1fr;
      }}
      .step-index {{
        width: 34px;
        height: 34px;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="panel">
      <div class="headline">
        <div>
          <div class="status-pill">{status_label}</div>
          <h1 style="margin-top:12px;">ARMS Init Activity Monitor</h1>
          <p>{summary}</p>
        </div>
        <div class="stat">
          <label>Report File</label>
          <strong>{report_path}</strong>
        </div>
      </div>
      <div class="stats">
        <div class="stat">
          <label>Project Root</label>
          <strong>{project_root}</strong>
        </div>
        <div class="stat">
          <label>ARMS Root</label>
          <strong>{arms_root}</strong>
        </div>
        <div class="stat">
          <label>Command</label>
          <strong>{command}</strong>
        </div>
        <div class="stat">
          <label>Mode</label>
          <strong>{mode}</strong>
        </div>
        <div class="stat">
          <label>Engine Version</label>
          <strong>{engine_version}</strong>
        </div>
        <div class="stat">
          <label>Updated</label>
          <strong>{updated_at}</strong>
        </div>
      </div>
    </section>

    <section class="panel">
      <h2>Step Timeline</h2>
      <div class="steps">
        {steps_markup}
      </div>
    </section>

    {error_markup}
  </main>
</body>
</html>
""".format(
            refresh=refresh,
            accent=STATUS_COLORS.get(self.status, "#6b7280"),
            status_label=html.escape(STATUS_LABELS.get(self.status, self.status.title())),
            summary=html.escape(self.summary),
            report_path=html.escape(self.report_path),
            project_root=html.escape(self.project_root),
            arms_root=html.escape(self.arms_root or "Pending"),
            command=html.escape(self.command),
            mode="YOLO" if self.is_yolo else "Standard",
            engine_version=html.escape(__version__),
            updated_at=html.escape(format_timestamp(self.updated_at)),
            steps_markup="".join(steps_markup),
            error_markup=error_markup,
        )
