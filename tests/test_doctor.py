import io
import os
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
    Path(path).mkdir(parents=True, exist_ok=True)
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(previous)


class DoctorCommandTests(unittest.TestCase):
    def invoke_cli(self, cwd, *args):
        stdout = io.StringIO()
        exit_code = 0
        with working_directory(cwd), mock.patch.object(sys, "argv", ["arms", *args]), redirect_stdout(stdout):
            try:
                init_arms.main()
            except SystemExit as exc:
                exit_code = exc.code if isinstance(exc.code, int) else 1
        return exit_code, stdout.getvalue()

    def test_doctor_passes_for_initialized_workspace_with_actionable_warnings(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nWorkspace health demo.\n", encoding="utf-8")

            exit_code, _ = self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))
            self.assertEqual(exit_code, 0)

            exit_code, output = self.invoke_cli(project_root, "doctor", "--root", str(ARMS_ROOT))

            self.assertEqual(exit_code, 0)
            self.assertIn("**Result:** PASS", output)
            self.assertIn("[OK] Required workspace files are present.", output)
            self.assertIn("[WARN] `arms fix issues` is waiting on a review report.", output)

    def test_doctor_exits_nonzero_for_missing_workspace_files(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nBroken workspace.\n", encoding="utf-8")

            exit_code, output = self.invoke_cli(project_root, "doctor", "--root", str(ARMS_ROOT))

            self.assertEqual(exit_code, 1)
            self.assertIn("Missing required workspace directories", output)
            self.assertIn("Run `arms init` to scaffold the managed workspace directories.", output)
            self.assertIn("Doctor found", output)

    def test_doctor_fails_when_engine_instructions_are_out_of_sync(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nWorkspace drift.\n", encoding="utf-8")

            exit_code, _ = self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))
            self.assertEqual(exit_code, 0)

            engine_path = project_root / ".arms" / "ENGINE.md"
            engine_path.write_text(engine_path.read_text(encoding="utf-8") + "\n# Drift\n", encoding="utf-8")

            exit_code, output = self.invoke_cli(project_root, "doctor", "--root", str(ARMS_ROOT))

            self.assertEqual(exit_code, 1)
            self.assertIn("`.arms/ENGINE.md` is out of sync", output)
            self.assertIn("Rerun `arms init` to resync `.arms/ENGINE.md`", output)


if __name__ == "__main__":
    unittest.main()
