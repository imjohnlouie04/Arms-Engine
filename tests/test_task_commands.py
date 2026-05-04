import io
import os
import re
import sys
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from arms_engine import init_arms


REPO_ROOT = Path(__file__).resolve().parents[1]
ARMS_ROOT = REPO_ROOT / "arms_engine"


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class TaskCommandTests(unittest.TestCase):
    def invoke_cli(self, cwd, *args):
        stdout = io.StringIO()
        exit_code = 0
        with working_directory(cwd), mock.patch.object(sys, "argv", ["arms", *args]), redirect_stdout(stdout):
            try:
                init_arms.main()
            except SystemExit as exc:
                exit_code = exc.code if isinstance(exc.code, int) else 1
        return exit_code, stdout.getvalue()

    def test_task_log_requires_initialized_workspace(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nTask routing.\n", encoding="utf-8")

            exit_code, output = self.invoke_cli(
                project_root,
                "task",
                "log",
                "--task",
                "Improve mobile dashboard layout",
                "--root",
                str(ARMS_ROOT),
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("run `arms init` first", output.lower())

    def test_task_log_infers_specialist_agent_and_updates_matching_row(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nTask routing.\n", encoding="utf-8")
            self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))

            exit_code, output = self.invoke_cli(
                project_root,
                "task",
                "log",
                "--task",
                "Improve responsive dashboard layout and mobile sidebar",
                "--status",
                "In Progress",
                "--root",
                str(ARMS_ROOT),
            )

            self.assertEqual(exit_code, 0)
            session_content = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            self.assertIn("arms-frontend-agent", session_content)
            self.assertRegex(session_content, r"\| \d+ \| Improve responsive dashboard layout and mobile sidebar \| arms-frontend-agent \| (frontend-design|ui-ux-pro-max) \|")
            self.assertIn("Task ID:", output)
            task_id_match = re.search(r"Task ID: `([^`]+)`", output)
            self.assertIsNotNone(task_id_match)
            task_id = task_id_match.group(1)

            exit_code, output = self.invoke_cli(
                project_root,
                "task",
                "log",
                "--task",
                "Improve responsive dashboard layout and mobile sidebar",
                "--status",
                "Blocked",
                "--root",
                str(ARMS_ROOT),
            )

            self.assertEqual(exit_code, 0)
            session_content = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            active_task_lines = [
                line
                for line in session_content.splitlines()
                if "| Improve responsive dashboard layout and mobile sidebar |" in line
            ]
            self.assertEqual(len(active_task_lines), 1)
            self.assertIn(
                "| {} | Improve responsive dashboard layout and mobile sidebar | arms-frontend-agent |".format(task_id),
                session_content,
            )
            self.assertIn(
                "Updated existing task row `#{}` instead of duplicating it.".format(task_id),
                output,
            )
            self.assertIn("Blocked", output)

    def test_task_update_can_reassign_agent_and_done_archives_the_row(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nTask archive.\n", encoding="utf-8")
            self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))

            _, log_output = self.invoke_cli(
                project_root,
                "task",
                "log",
                "--task",
                "Harden auth token validation",
                "--root",
                str(ARMS_ROOT),
            )
            task_id_match = re.search(r"Task ID: `([^`]+)`", log_output)
            self.assertIsNotNone(task_id_match)
            task_id = task_id_match.group(1)

            exit_code, update_output = self.invoke_cli(
                project_root,
                "task",
                "update",
                "--task-id",
                task_id,
                "--assigned-agent",
                "arms-security-agent",
                "--status",
                "In Progress",
                "--root",
                str(ARMS_ROOT),
            )

            self.assertEqual(exit_code, 0)
            session_content = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            self.assertIn("arms-security-agent", session_content)
            self.assertIn("security-code-review", session_content)
            self.assertIn("In Progress", update_output)

            exit_code, done_output = self.invoke_cli(
                project_root,
                "task",
                "done",
                "--task-id",
                task_id,
                "--root",
                str(ARMS_ROOT),
            )

            self.assertEqual(exit_code, 0)
            session_content = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            archive_content = (project_root / ".arms" / "SESSION_ARCHIVE.md").read_text(encoding="utf-8")
            self.assertNotIn("Harden auth token validation", session_content)
            self.assertIn("Harden auth token validation", archive_content)
            self.assertIn("### Context: Task command: complete row", archive_content)
            self.assertIn("## Archive Diagnostics", done_output)

    def test_task_routing_uses_word_boundaries_for_keyword_matches(self):
        self.assertEqual(init_arms.infer_agent_from_task("Add API endpoint for auth"), "arms-backend-agent")
        self.assertEqual(init_arms.infer_agent_from_task("Add QA regression coverage"), "arms-qa-agent")
        self.assertEqual(init_arms.infer_agent_from_task("Review capital allocation memo"), "arms-main-agent")
        self.assertEqual(init_arms.infer_agent_from_task("Document attestation flow"), "arms-main-agent")


class DependencyCycleTests(unittest.TestCase):
    """Unit tests for parse_dependency_ids and detect_dependency_cycle."""

    def _rows(self, *dep_pairs):
        """Build a minimal rows list from (id, dep_value) tuples."""
        return [{"#": rid, "Dependencies": dep} for rid, dep in dep_pairs]

    def test_parse_empty_dep_value(self):
        from arms_engine.tasks import parse_dependency_ids
        self.assertEqual(parse_dependency_ids("—"), set())
        self.assertEqual(parse_dependency_ids(""), set())
        self.assertEqual(parse_dependency_ids("-"), set())

    def test_parse_single_dep(self):
        from arms_engine.tasks import parse_dependency_ids
        self.assertEqual(parse_dependency_ids("1"), {"1"})

    def test_parse_multiple_deps(self):
        from arms_engine.tasks import parse_dependency_ids
        self.assertEqual(parse_dependency_ids("1, 2, 3"), {"1", "2", "3"})

    def test_no_cycle_when_deps_are_empty(self):
        from arms_engine.tasks import detect_dependency_cycle
        rows = self._rows(("1", "—"), ("2", "1"))
        self.assertEqual(detect_dependency_cycle(rows, "3", {"2"}), [])

    def test_direct_cycle_detected(self):
        from arms_engine.tasks import detect_dependency_cycle
        # Task 2 depends on 1; if we make task 1 depend on 2 → cycle 1→2→1
        rows = self._rows(("1", "—"), ("2", "1"))
        cycle = detect_dependency_cycle(rows, "1", {"2"})
        self.assertTrue(cycle, "Expected a cycle to be detected")

    def test_transitive_cycle_detected(self):
        from arms_engine.tasks import detect_dependency_cycle
        # 2→1, 3→2; making 1→3 creates 1→3→2→1
        rows = self._rows(("1", "—"), ("2", "1"), ("3", "2"))
        cycle = detect_dependency_cycle(rows, "1", {"3"})
        self.assertTrue(cycle)

    def test_no_false_positive_for_valid_deps(self):
        from arms_engine.tasks import detect_dependency_cycle
        rows = self._rows(("1", "—"), ("2", "1"), ("3", "1"))
        # Task 4 depending on 2 and 3 is fine
        self.assertEqual(detect_dependency_cycle(rows, "4", {"2", "3"}), [])


class PipeEscapeRoundTripTests(unittest.TestCase):
    """Verify that task text containing | survives a render→parse round-trip."""

    def _make_rows(self, task_text):
        return [
            {
                "#": "1",
                "Task": task_text,
                "Assigned Agent": "arms-main-agent",
                "Active Skill": "—",
                "Dependencies": "—",
                "Status": "Pending",
            }
        ]

    def _round_trip(self, task_text, arms_root):
        from arms_engine.protocols import parse_task_rows, render_task_table
        rendered = render_task_table(self._make_rows(task_text), str(arms_root))
        rows = parse_task_rows(rendered)
        return rows[0]["Task"] if rows else None

    def test_plain_task_text_survives(self):
        ARMS_ROOT = Path(__file__).resolve().parents[1] / "arms_engine"
        result = self._round_trip("Deploy the API", ARMS_ROOT)
        self.assertEqual(result, "Deploy the API")

    def test_pipe_in_task_text_survives(self):
        ARMS_ROOT = Path(__file__).resolve().parents[1] / "arms_engine"
        result = self._round_trip("Evaluate option A | option B", ARMS_ROOT)
        self.assertEqual(result, "Evaluate option A | option B")

    def test_multiple_pipes_survive(self):
        ARMS_ROOT = Path(__file__).resolve().parents[1] / "arms_engine"
        result = self._round_trip("A | B | C", ARMS_ROOT)
        self.assertEqual(result, "A | B | C")


class TaskListCommandTests(unittest.TestCase):
    """Arms task list/status is a read-only introspection command."""

    def test_identify_task_list_command(self):
        from arms_engine.tasks import identify_task_command
        self.assertEqual(identify_task_command(("task", "list")), "list")

    def test_identify_task_status_alias(self):
        from arms_engine.tasks import identify_task_command
        self.assertEqual(identify_task_command(("task", "status")), "list")

    def test_list_rows_returns_table_string(self):
        from arms_engine.tasks import list_task_rows
        ARMS_ROOT = Path(__file__).resolve().parents[1] / "arms_engine"
        rows = [
            {
                "#": "1",
                "Task": "Write tests",
                "Assigned Agent": "arms-qa-agent",
                "Active Skill": "qa-automation-testing",
                "Dependencies": "—",
                "Status": "In Progress",
            }
        ]
        result = list_task_rows(rows, str(ARMS_ROOT))
        self.assertIn("Write tests", result)
        self.assertIn("arms-qa-agent", result)

    def test_list_rows_empty_returns_message(self):
        from arms_engine.tasks import list_task_rows
        ARMS_ROOT = Path(__file__).resolve().parents[1] / "arms_engine"
        result = list_task_rows([], str(ARMS_ROOT))
        self.assertIn("No active tasks", result)


if __name__ == "__main__":
    unittest.main()
