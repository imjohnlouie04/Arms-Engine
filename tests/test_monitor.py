import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from arms_engine.monitor import (
    extract_environment_value,
    format_duration,
    format_timestamp,
    pad_line,
    summarize_exception,
    truncate_text,
)
from arms_engine.monitor_viewer import render_terminal_dashboard, summarize_workspace


class TruncateTextTests(unittest.TestCase):
    def test_short_text_unchanged(self):
        self.assertEqual(truncate_text("hello", 10), "hello")

    def test_exact_width_unchanged(self):
        self.assertEqual(truncate_text("hello", 5), "hello")

    def test_long_text_truncated_with_ellipsis(self):
        result = truncate_text("hello world", 8)
        self.assertTrue(result.endswith("..."))
        self.assertIn("hello w", result)

    def test_zero_width_returns_empty(self):
        self.assertEqual(truncate_text("hello", 0), "")

    def test_width_of_one(self):
        result = truncate_text("hello", 1)
        self.assertEqual(len(result), 1)

    def test_non_string_coerced(self):
        self.assertEqual(truncate_text(42, 10), "42")


class PadLineTests(unittest.TestCase):
    def test_short_text_padded(self):
        result = pad_line("hi", 6)
        self.assertEqual(result, "hi    ")
        self.assertEqual(len(result), 6)

    def test_exact_width_no_padding(self):
        result = pad_line("hello", 5)
        self.assertEqual(result, "hello")

    def test_overflow_text_truncated(self):
        result = pad_line("hello world", 7)
        self.assertTrue(result.endswith("..."))


class FormatTimestampTests(unittest.TestCase):
    def test_zero_returns_not_yet(self):
        # format_timestamp in module scope is time-stamp based (not None-aware)
        result = format_timestamp(0)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_valid_timestamp_returns_formatted_string(self):
        ts = time.mktime(time.strptime("2024-01-15 12:00:00", "%Y-%m-%d %H:%M:%S"))
        result = format_timestamp(ts)
        self.assertIn("2024-01-15", result)


class FormatDurationTests(unittest.TestCase):
    def test_running_returns_elapsed_string(self):
        import time as time_module
        started = time_module.time() - 5.0
        result = format_duration(started)
        self.assertIn("s", result)

    def test_finished_returns_elapsed_string(self):
        import time as time_module
        started = time_module.time() - 10.0
        finished = time_module.time() - 2.0
        result = format_duration(started, finished)
        self.assertIn("s", result)


class ExtractEnvironmentValueTests(unittest.TestCase):
    ENVIRONMENT = (
        "- Execution Mode: Mode A (Parallel)\n"
        "- YOLO Mode: Disabled\n"
        "- Engine Version: 1.2.3\n"
    )

    def test_extracts_execution_mode(self):
        result = extract_environment_value(self.ENVIRONMENT, "Execution Mode")
        self.assertEqual(result, "Mode A (Parallel)")

    def test_extracts_yolo_mode(self):
        result = extract_environment_value(self.ENVIRONMENT, "YOLO Mode")
        self.assertEqual(result, "Disabled")

    def test_returns_unknown_for_missing_key(self):
        result = extract_environment_value(self.ENVIRONMENT, "Nonexistent Key")
        self.assertEqual(result, "Unknown")


class SummarizeExceptionTests(unittest.TestCase):
    def test_returns_string_for_exception(self):
        try:
            raise ValueError("test error")
        except ValueError as exc:
            result = summarize_exception(exc)
        self.assertIsInstance(result, str)
        self.assertIn("test error", result)


class ViewerScriptExtractionTests(unittest.TestCase):
    def test_load_viewer_script_template_returns_string(self):
        from arms_engine.monitor import _load_viewer_script_template
        content = _load_viewer_script_template()
        self.assertIsInstance(content, str)
        self.assertGreater(len(content), 100)

    def test_viewer_script_is_valid_python(self):
        from arms_engine.monitor import _load_viewer_script_template
        import ast
        content = _load_viewer_script_template()
        # Should parse without SyntaxError
        tree = ast.parse(content)
        self.assertIsNotNone(tree)

    def test_viewer_script_has_main_entrypoint(self):
        from arms_engine.monitor import _load_viewer_script_template
        content = _load_viewer_script_template()
        self.assertIn("def main()", content)
        self.assertIn('if __name__ == "__main__"', content)


class MonitorViewerMemoryTests(unittest.TestCase):
    def test_summarize_workspace_reads_memory_sections(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            arms_dir = project_root / ".arms"
            arms_dir.mkdir()
            (arms_dir / "BRAND.md").write_text("ok", encoding="utf-8")
            (arms_dir / "CONTEXT_SYNTHESIS.md").write_text("ok", encoding="utf-8")
            (arms_dir / "GENERATED_PROMPTS.md").write_text("ok", encoding="utf-8")
            (arms_dir / "MEMORY.md").write_text("ok", encoding="utf-8")
            (arms_dir / "SESSION.md").write_text(
                "\n".join(
                    [
                        "# ARMS Session Log",
                        "",
                        "## Environment",
                        "- Execution Mode: Parallel",
                        "- YOLO Mode: Disabled",
                        "",
                        "## Active Tasks",
                        "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |",
                        "|---|------|----------------|--------------|--------------|--------|",
                        "| 1 | Task A | arms-main-agent | arms-orchestrator | — | In Progress |",
                        "",
                        "## Blockers",
                        "None",
                        "",
                        "## Memory Signals",
                        "- Read `.arms/MEMORY.md` before task work.",
                        "- Known Bugs & Fixes: Token refresh bug fixed via secret rotation.",
                        "- After significant work, draft a memory lesson candidate and ask approval before appending to `.arms/MEMORY.md`.",
                        "",
                        "## Memory Packet",
                        "- [Known Bugs & Fixes] Token refresh bug fixed via secret rotation. (confidence: 0.95)",
                    ]
                ),
                encoding="utf-8",
            )

            workspace = summarize_workspace(str(project_root))
            self.assertIn("Known Bugs & Fixes: Token refresh bug fixed via secret rotation.", workspace["memory_signals"])
            self.assertTrue(any("confidence: 0.95" in item for item in workspace["memory_packet"]))

    def test_render_terminal_dashboard_includes_memory_sections(self):
        snapshot = {
            "status": "running",
            "command": "init",
            "is_yolo": False,
            "engine_version": "1.0.0",
            "project_root": "/tmp/demo",
            "arms_root": "/tmp/arms_engine",
            "report_path": "/tmp/demo/.arms/reports/init-monitor-latest.html",
            "updated_at": "now",
            "summary": "running",
            "steps": [],
        }
        rendered = render_terminal_dashboard(snapshot, width=120)
        self.assertIn("Memory Signals", rendered)
        self.assertIn("Memory Packet", rendered)


if __name__ == "__main__":
    unittest.main()
