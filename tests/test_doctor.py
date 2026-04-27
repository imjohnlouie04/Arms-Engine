import io
import os
import sys
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from arms_engine import init_arms
from arms_engine.session import read_text_file


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

    def test_doctor_fails_when_agent_mirror_content_is_stale(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nAgent drift.\n", encoding="utf-8")

            exit_code, _ = self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))
            self.assertEqual(exit_code, 0)

            agent_path = project_root / ".gemini" / "agents" / "arms-main-agent.md"
            agent_path.write_text(
                agent_path.read_text(encoding="utf-8").replace(
                    "Must ask for explicit user approval before updating `.arms/MEMORY.md`.",
                    "Stale mirrored content.",
                ),
                encoding="utf-8",
            )

            exit_code, output = self.invoke_cli(project_root, "doctor", "--root", str(ARMS_ROOT))

            self.assertEqual(exit_code, 1)
            self.assertIn("Agent mirrors are out of sync", output)
            self.assertIn("`.gemini/agents` has stale content", output)
            self.assertIn("arms-main-agent.md", output)
            self.assertIn("Rerun `arms init` to resync `.gemini/agents/` and `.github/agents/`", output)

    def test_doctor_fails_when_gemini_agents_yaml_is_out_of_sync(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nRegistry drift.\n", encoding="utf-8")

            exit_code, _ = self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))
            self.assertEqual(exit_code, 0)

            agents_yaml_path = project_root / ".gemini" / "agents.yaml"
            agents_yaml_path.write_text(agents_yaml_path.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")

            exit_code, output = self.invoke_cli(project_root, "doctor", "--root", str(ARMS_ROOT))

            self.assertEqual(exit_code, 1)
            self.assertIn("Mirrored agent registry file `.gemini/agents.yaml` is out of sync", output)
            self.assertIn("Rerun `arms init` to resync `.gemini/agents.yaml`", output)

    def test_doctor_fix_resyncs_engine_owned_files_without_touching_project_instructions(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nDoctor repair.\n", encoding="utf-8")

            exit_code, _ = self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))
            self.assertEqual(exit_code, 0)

            engine_source = read_text_file(str(ARMS_ROOT / "ENGINE.md"))
            agents_yaml_source = read_text_file(str(ARMS_ROOT / "agents.yaml"))
            agent_source = read_text_file(str(ARMS_ROOT / "agents" / "arms-main-agent.md"))

            (project_root / ".arms" / "ENGINE.md").write_text("stale engine\n", encoding="utf-8")
            (project_root / ".gemini" / "agents.yaml").write_text("stale registry\n", encoding="utf-8")
            (project_root / ".gemini" / "agents" / "arms-main-agent.md").write_text("stale agent\n", encoding="utf-8")
            project_instruction_path = project_root / ".github" / "copilot-instructions.md"
            project_instruction_path.parent.mkdir(parents=True, exist_ok=True)
            project_instruction_path.write_text("project-owned instructions\n", encoding="utf-8")

            exit_code, output = self.invoke_cli(project_root, "doctor", "--fix", "--root", str(ARMS_ROOT))

            self.assertEqual(exit_code, 0)
            self.assertIn("**Result:** PASS", output)
            self.assertIn("### Repair Mode", output)
            self.assertIn("[FIXED] Resynced `.gemini/agents/` and `.gemini/agents.yaml` from the engine.", output)
            self.assertEqual((project_root / ".arms" / "ENGINE.md").read_text(encoding="utf-8"), engine_source)
            self.assertEqual((project_root / ".gemini" / "agents.yaml").read_text(encoding="utf-8"), agents_yaml_source)
            self.assertNotEqual((project_root / ".gemini" / "agents" / "arms-main-agent.md").read_text(encoding="utf-8"), "stale agent\n")
            self.assertIn("## Runtime Rules", (project_root / ".gemini" / "agents" / "arms-main-agent.md").read_text(encoding="utf-8"))
            self.assertNotEqual(agent_source, "stale agent\n")
            self.assertEqual(project_instruction_path.read_text(encoding="utf-8"), "project-owned instructions\n")

    def test_doctor_fix_does_not_bootstrap_missing_workspace(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nMissing workspace.\n", encoding="utf-8")

            exit_code, output = self.invoke_cli(project_root, "doctor", "--fix", "--root", str(ARMS_ROOT))

            self.assertEqual(exit_code, 1)
            self.assertIn("Missing required workspace directories", output)
            self.assertIn("Skipped automatic repair because `.arms/SESSION.md` is missing", output)
            self.assertFalse((project_root / ".arms" / "ENGINE.md").exists())


if __name__ == "__main__":
    unittest.main()
