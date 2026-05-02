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
            self.assertEqual(session_content.count("Improve responsive dashboard layout and mobile sidebar"), 1)
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


if __name__ == "__main__":
    unittest.main()
