import io
import os
import sys
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from arms_engine import init_arms
from arms_engine import doctor as doctor_module
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
            self.assertIn("Version Diagnostics", output)
            self.assertIn("Version sources:", output)
            self.assertIn("### Final Triage", output)
            self.assertIn("Blocking issues: none.", output)

    def test_doctor_exits_nonzero_for_missing_workspace_files(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nBroken workspace.\n", encoding="utf-8")

            exit_code, output = self.invoke_cli(project_root, "doctor", "--root", str(ARMS_ROOT))

            self.assertEqual(exit_code, 1)
            self.assertIn("Missing required workspace directories", output)
            self.assertIn("Run `arms init` to scaffold the managed workspace directories.", output)
            self.assertIn("Doctor found", output)
            self.assertIn("### Final Triage", output)

    def test_doctor_fails_when_token_budgets_are_exceeded(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "pyproject.toml").write_text(
                "[project]\nname = 'budget-demo'\ndescription = 'Budget drift workspace.'\n",
                encoding="utf-8",
            )

            exit_code, _ = self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))
            self.assertEqual(exit_code, 0)

            (project_root / ".arms" / "SESSION.md").write_text(
                read_text_file(str(project_root / ".arms" / "SESSION.md")) + ("\nextra " * 2000),
                encoding="utf-8",
            )
            (project_root / ".arms" / "CONTEXT_SYNTHESIS.md").write_text(
                read_text_file(str(project_root / ".arms" / "CONTEXT_SYNTHESIS.md")) + ("\nbrief " * 3000),
                encoding="utf-8",
            )

            exit_code, output = self.invoke_cli(project_root, "doctor", "--root", str(ARMS_ROOT))

            self.assertEqual(exit_code, 1)
            self.assertIn("Context Budgets", output)
            self.assertIn("`.arms/SESSION.md` uses", output)
            self.assertIn("`.arms/CONTEXT_SYNTHESIS.md` uses", output)
            self.assertIn("### Final Triage", output)
            self.assertIn("Blocking issues (", output)

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

    def test_doctor_warns_when_runtime_version_differs_from_git_describe(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nVersion diagnostics.\n", encoding="utf-8")

            exit_code, _ = self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))
            self.assertEqual(exit_code, 0)

            with mock.patch.object(
                doctor_module,
                "collect_version_diagnostics",
                return_value={
                    "runtime_version": "1.7.1",
                    "git_describe_raw": "v1.7.2-1-gabc1234",
                    "git_describe_version": "1.7.2.dev1+gabc1234",
                    "latest_tag": "v1.7.2",
                    "generated_version": "1.7.0",
                    "installed_version": "1.7.1",
                },
            ):
                exit_code, output = self.invoke_cli(project_root, "doctor", "--root", str(ARMS_ROOT))

            self.assertEqual(exit_code, 0)
            self.assertIn("Runtime version `1.7.1` does not match git describe `1.7.2.dev1+gabc1234`.", output)
            self.assertIn("Version sources:", output)

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

    def test_doctor_warns_when_project_owned_instructions_lack_task_intake_guidance(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nProject instruction drift.\n", encoding="utf-8")

            exit_code, _ = self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))
            self.assertEqual(exit_code, 0)

            project_instruction_path = project_root / ".github" / "copilot-instructions.md"
            project_instruction_path.parent.mkdir(parents=True, exist_ok=True)
            project_instruction_path.write_text("project-owned instructions\n", encoding="utf-8")

            exit_code, output = self.invoke_cli(project_root, "doctor", "--root", str(ARMS_ROOT))

            self.assertEqual(exit_code, 0)
            self.assertIn("Project-owned instruction files are missing ARMS task-intake guidance", output)
            self.assertIn("`arms task log` / `arms task update` semantics", output)

    def test_doctor_ok_when_project_owned_instructions_include_task_intake_guidance(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nProject instruction aligned.\n", encoding="utf-8")

            exit_code, _ = self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))
            self.assertEqual(exit_code, 0)

            project_instruction_path = project_root / ".github" / "copilot-instructions.md"
            project_instruction_path.parent.mkdir(parents=True, exist_ok=True)
            project_instruction_path.write_text(
                "Read .arms/SESSION.md first and use arms task log semantics for durable asks.\n",
                encoding="utf-8",
            )

            exit_code, output = self.invoke_cli(project_root, "doctor", "--root", str(ARMS_ROOT))

            self.assertEqual(exit_code, 0)
            self.assertIn("Project-owned instruction files include ARMS task-intake guidance for normal chat.", output)

    def test_doctor_fix_reports_removed_obsolete_skill_artifacts(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nDoctor cleanup report.\n", encoding="utf-8")

            exit_code, _ = self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))
            self.assertEqual(exit_code, 0)

            obsolete_dir = project_root / ".gemini" / "skills"
            obsolete_dir.mkdir(parents=True)
            (obsolete_dir / "stale").mkdir()
            (project_root / ".gemini" / "skills.yaml").write_text("stale\n", encoding="utf-8")

            exit_code, output = self.invoke_cli(project_root, "doctor", "--fix", "--root", str(ARMS_ROOT))

            self.assertEqual(exit_code, 0)
            self.assertIn("Removed obsolete Gemini skill artifacts", output)
            self.assertIn("`.gemini/skills`", output)
            self.assertIn("`.gemini/skills.yaml`", output)

    def test_doctor_fix_does_not_bootstrap_missing_workspace(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nMissing workspace.\n", encoding="utf-8")

            exit_code, output = self.invoke_cli(project_root, "doctor", "--fix", "--root", str(ARMS_ROOT))

            self.assertEqual(exit_code, 1)
            self.assertIn("Missing required workspace directories", output)
            self.assertIn("Skipped automatic repair because `.arms/SESSION.md` is missing", output)
            self.assertFalse((project_root / ".arms" / "ENGINE.md").exists())

    def test_release_check_passes_with_shipping_summary(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nRelease validation.\n", encoding="utf-8")

            exit_code, _ = self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))
            self.assertEqual(exit_code, 0)

            exit_code, output = self.invoke_cli(project_root, "release", "check", "--root", str(ARMS_ROOT))

            self.assertEqual(exit_code, 0)
            self.assertIn("## Release Validation", output)
            self.assertIn("**Release Gate:** READY WITH WARNINGS", output)
            self.assertIn("### Shipping Summary", output)
            self.assertIn("Version snapshot:", output)
            self.assertIn("Protocol Readiness", output)
            self.assertIn("arms run deploy", output)

    def test_release_check_exits_nonzero_when_workspace_is_missing(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nMissing release workspace.\n", encoding="utf-8")

            exit_code, output = self.invoke_cli(project_root, "release", "check", "--root", str(ARMS_ROOT))

            self.assertEqual(exit_code, 1)
            self.assertIn("**Release Gate:** BLOCKED", output)
            self.assertIn("Blocking categories", output)
            self.assertIn("Workspace Health", output)
            self.assertIn("Release validation found blocking issues", output)

    def test_release_check_rejects_fix_flag(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nRelease fix rejection.\n", encoding="utf-8")

            exit_code, output = self.invoke_cli(project_root, "release", "check", "--fix", "--root", str(ARMS_ROOT))

            self.assertEqual(exit_code, 1)
            self.assertIn("`--fix` is only supported with `arms doctor`", output)


class BrandDriftTests(unittest.TestCase):
    """Unit tests for check_brand_drift in doctor.py."""

    def _make_brand(self, tmpdir, content):
        arms_dir = Path(tmpdir) / ".arms"
        arms_dir.mkdir(exist_ok=True)
        (arms_dir / "BRAND.md").write_text(content, encoding="utf-8")

    def test_no_drift_when_brand_md_missing(self):
        with TemporaryDirectory() as tmp:
            warnings = doctor_module.check_brand_drift(tmp)
            self.assertEqual(warnings, [])

    def test_no_drift_when_brand_fully_answered(self):
        brand_content = (
            "# Brand Context\n"
            "- **Project Name:** MyProject\n"
            "- **Mission:** Build great things.\n"
            "- **Vision:** World domination.\n"
            "- **Personality:** Bold.\n"
            "- **Voice & Tone:** Direct.\n"
            "- **Primary Audience:** Developers.\n"
            "- **Core Values:** Quality.\n"
            "- **Differentiation:** Speed.\n"
            "- **Color Palette:** Blue.\n"
            "- **Typography:** Inter.\n"
            "- **Logo Status:** Done.\n"
            "- **Visual Direction:** Clean.\n"
            "- **Experience Type:** SaaS.\n"
            "- **Technical Constraints:** None.\n"
            "- **Preferred Tech Stack:** Next.js.\n"
            "- **Authentication Requirement:** JWT.\n"
            "- **Deployment Target:** Vercel.\n"
        )
        with TemporaryDirectory() as tmp:
            self._make_brand(tmp, brand_content)
            warnings = doctor_module.check_brand_drift(tmp)
            self.assertEqual(warnings, [])

    def test_warns_on_tbd_fields_with_pyproject_present(self):
        brand_content = (
            "# Brand Context\n"
            "> New project detected.\n"
            "- **Project Name:** TBD\n"
            "- **Mission:** TBD\n"
        )
        with TemporaryDirectory() as tmp:
            self._make_brand(tmp, brand_content)
            Path(tmp, "pyproject.toml").write_text(
                '[project]\nname = "myproject"\ndescription = "Test"\n', encoding="utf-8"
            )
            warnings = doctor_module.check_brand_drift(tmp)
            self.assertTrue(any("unanswered" in w for w in warnings))

    def test_warns_on_project_name_mismatch(self):
        brand_content = (
            "# Brand Context\n"
            "- **Project Name:** old-name\n"
        )
        with TemporaryDirectory() as tmp:
            self._make_brand(tmp, brand_content)
            Path(tmp, "pyproject.toml").write_text(
                '[project]\nname = "new-name"\ndescription = "Test"\n', encoding="utf-8"
            )
            warnings = doctor_module.check_brand_drift(tmp)
            self.assertTrue(any("does not match" in w for w in warnings))

    def test_no_mismatch_when_names_agree(self):
        brand_content = (
            "# Brand Context\n"
            "- **Project Name:** MyProject\n"
        )
        with TemporaryDirectory() as tmp:
            self._make_brand(tmp, brand_content)
            Path(tmp, "pyproject.toml").write_text(
                '[project]\nname = "MyProject"\ndescription = "Test"\n', encoding="utf-8"
            )
            warnings = doctor_module.check_brand_drift(tmp)
            mismatch_warnings = [w for w in warnings if "does not match" in w]
            self.assertEqual(mismatch_warnings, [])


if __name__ == "__main__":
    unittest.main()
