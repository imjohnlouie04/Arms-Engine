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


class MemoryCommandTests(unittest.TestCase):
    def invoke_cli(self, cwd, *args):
        stdout = io.StringIO()
        exit_code = 0
        with working_directory(cwd), mock.patch.object(sys, "argv", ["arms", *args]), redirect_stdout(stdout):
            try:
                init_arms.main()
            except SystemExit as exc:
                exit_code = exc.code if isinstance(exc.code, int) else 1
        return exit_code, stdout.getvalue()

    def test_memory_draft_requires_initialized_workspace(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nMemory workflow.\n", encoding="utf-8")

            exit_code, output = self.invoke_cli(
                project_root,
                "memory",
                "draft",
                "--section",
                "Known Bugs & Fixes",
                "--lesson",
                "Preserve session memory signals.",
                "--root",
                str(ARMS_ROOT),
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("run `arms init` first", output.lower())

    def test_memory_draft_records_pending_entry_without_refreshing_session_signals(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nMemory draft.\n", encoding="utf-8")
            self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))

            exit_code, output = self.invoke_cli(
                project_root,
                "memory",
                "draft",
                "--section",
                "Known Bugs & Fixes",
                "--lesson",
                "Preserve session memory signals during re-init.",
                "--root",
                str(ARMS_ROOT),
            )

            self.assertEqual(exit_code, 0)
            memory_content = (project_root / ".arms" / "MEMORY.md").read_text(encoding="utf-8")
            session_content = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            self.assertRegex(
                memory_content,
                r"\[PENDING APPROVAL\]\[memory-\d{8}-\d{2}\]: Preserve session memory signals during re-init\.",
            )
            self.assertNotIn("Known Bugs & Fixes: Preserve session memory signals during re-init.", session_content)
            self.assertIn("Draft ID:", output)

    def test_memory_append_approves_draft_and_refreshes_session(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nMemory append.\n", encoding="utf-8")
            self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))

            _, draft_output = self.invoke_cli(
                project_root,
                "memory",
                "draft",
                "--section",
                "Developer Preferences",
                "--lesson",
                "Prefer structured memory commands over manual copy-paste.",
                "--root",
                str(ARMS_ROOT),
            )
            draft_match = re.search(r"Draft ID: `([^`]+)`", draft_output)
            self.assertIsNotNone(draft_match)
            draft_id = draft_match.group(1)

            exit_code, output = self.invoke_cli(
                project_root,
                "memory",
                "append",
                "--draft-id",
                draft_id,
                "--root",
                str(ARMS_ROOT),
            )

            self.assertEqual(exit_code, 0)
            memory_content = (project_root / ".arms" / "MEMORY.md").read_text(encoding="utf-8")
            session_content = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            self.assertIn(f"[APPROVED][{draft_id}]: Prefer structured memory commands over manual copy-paste.", memory_content)
            self.assertNotIn(f"[PENDING APPROVAL][{draft_id}]", memory_content)
            self.assertIn(
                "Developer Preferences: Prefer structured memory commands over manual copy-paste.",
                session_content,
            )
            self.assertIn("Session memory signals refreshed", output)

    def test_memory_append_can_write_approved_entry_directly(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nDirect memory append.\n", encoding="utf-8")
            self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))

            exit_code, _ = self.invoke_cli(
                project_root,
                "memory",
                "append",
                "--section",
                "Known Bugs & Fixes",
                "--lesson",
                "Use approval markers so pending memory never leaks into hot context.",
                "--root",
                str(ARMS_ROOT),
            )

            self.assertEqual(exit_code, 0)
            memory_content = (project_root / ".arms" / "MEMORY.md").read_text(encoding="utf-8")
            session_content = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            self.assertRegex(
                memory_content,
                r"\[APPROVED\]\[memory-\d{8}-\d{2}\]: Use approval markers so pending memory never leaks into hot context\.",
            )
            self.assertIn(
                "Known Bugs & Fixes: Use approval markers so pending memory never leaks into hot context.",
                session_content,
            )


if __name__ == "__main__":
    unittest.main()
