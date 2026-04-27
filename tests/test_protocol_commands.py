import io
import os
import sys
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from arms_engine import init_arms
from arms_engine import protocols as protocols_module


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


def write_session(project_root, active_tasks="", completed_tasks="- None", blockers="None"):
    session_content = """# ARMS Session Log
Generated: old

## Environment
- ARMS Root: {arms_root}
- Engine Version: {engine_version}
- Project Root: {project_root}
- Project Name: Demo
- Execution Mode: Parallel
- YOLO Mode: Disabled

## Active Agents
- arms-main-agent
- arms-frontend-agent
- arms-backend-agent
- arms-devops-agent
- arms-security-agent
- arms-qa-agent

## Active Skills
- arms-orchestrator [Active]
- frontend-design
- backend-system-architect
- devops-orchestrator
- security-code-review
- qa-automation-testing

## Active Tasks
{active_tasks}

## Completed Tasks
{completed_tasks}

## Blockers
{blockers}
""".format(
        arms_root=ARMS_ROOT,
        engine_version=init_arms.__version__,
        project_root=project_root,
        active_tasks=active_tasks
        or (
            "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
            "|---|------|----------------|--------------|--------------|--------|"
        ),
        completed_tasks=completed_tasks,
        blockers=blockers,
    )
    (project_root / ".arms" / "SESSION.md").write_text(session_content, encoding="utf-8")


class ProtocolCommandTests(unittest.TestCase):
    def invoke_cli(self, cwd, *args):
        stdout = io.StringIO()
        with working_directory(cwd), mock.patch.object(sys, "argv", ["arms", *args]), redirect_stdout(stdout):
            init_arms.main()
        return stdout.getvalue()

    def test_run_review_updates_session_and_creates_review_report(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".arms" / "reports").mkdir(parents=True)
            write_session(
                project_root,
                active_tasks=(
                    "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
                    "|---|------|----------------|--------------|--------------|--------|\n"
                    "| 1 | Existing task | arms-main-agent | arms-orchestrator | — | Pending |"
                ),
            )

            output = self.invoke_cli(project_root, "--root", str(ARMS_ROOT), "run", "review")

            session = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            reports = sorted((project_root / ".arms" / "reports").glob("review-*.md"))

            self.assertIn("Review protocol staged and logged", output)
            self.assertIn("Existing task", session)
            self.assertIn("Review: audit architecture, validation, and code quality", session)
            self.assertEqual(len(reports), 1)
            self.assertIn("## Actionable Issues", reports[0].read_text(encoding="utf-8"))

    def test_fix_issues_parses_actionable_review_items_into_task_plan(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            reports_dir = project_root / ".arms" / "reports"
            reports_dir.mkdir(parents=True)
            write_session(project_root)
            (reports_dir / "review-2026-04-27.md").write_text(
                """# ARMS Review Report

## Actionable Issues
- Fix the mobile sidebar overlap on portrait tablets
- Resolve failing CI workflow for release builds
- Patch token validation for API sessions
""",
                encoding="utf-8",
            )

            output = self.invoke_cli(project_root, "--root", str(ARMS_ROOT), "fix", "issues")

            session = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            fix_plans = sorted(reports_dir.glob("fix-plan-*.md"))

            self.assertIn("Task plan generated and logged", output)
            self.assertIn("arms-frontend-agent", session)
            self.assertIn("arms-devops-agent", session)
            self.assertIn("arms-backend-agent", session)
            self.assertIn("Fix: Patch token validation for API sessions", session)
            self.assertEqual(len(fix_plans), 1)
            self.assertIn("## Parsed Issues", fix_plans[0].read_text(encoding="utf-8"))

    def test_fix_issues_sets_blocker_when_no_actionable_items_exist(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            reports_dir = project_root / ".arms" / "reports"
            reports_dir.mkdir(parents=True)
            write_session(project_root)
            (reports_dir / "review-2026-04-27.md").write_text(
                """# ARMS Review Report

## Actionable Issues
<!-- Add one bullet per actionable issue before running `arms fix issues`. -->
""",
                encoding="utf-8",
            )

            output = self.invoke_cli(project_root, "--root", str(ARMS_ROOT), "fix", "issues")
            session = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")

            self.assertIn("No actionable issues found", output)
            self.assertIn("No actionable issues found", session)

    def test_run_deploy_creates_release_notes_and_deploy_tasks(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".arms" / "reports").mkdir(parents=True)
            write_session(project_root)

            def fake_subprocess_run(command, capture_output, text, check):
                if "rev-parse" in command:
                    return protocols_module.subprocess.CompletedProcess(command, 0, stdout="true\n", stderr="")
                if "describe" in command:
                    return protocols_module.subprocess.CompletedProcess(command, 0, stdout="v1.0.0\n", stderr="")
                if "log" in command:
                    return protocols_module.subprocess.CompletedProcess(
                        command,
                        0,
                        stdout="feat(cli): add protocol command handlers\nfix(session): preserve blockers\n",
                        stderr="",
                    )
                raise AssertionError("Unexpected git command: {}".format(command))

            with mock.patch.object(protocols_module.subprocess, "run", side_effect=fake_subprocess_run):
                output = self.invoke_cli(project_root, "--root", str(ARMS_ROOT), "run", "deploy")

            session = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            notes = sorted((project_root / ".arms" / "reports").glob("release-notes-*.md"))

            self.assertIn("Pre-flight tasks staged and release notes generated", output)
            self.assertIn("Deploy: verify clean working tree and production build readiness", session)
            self.assertEqual(len(notes), 1)
            release_notes = notes[0].read_text(encoding="utf-8")
            self.assertIn("Added protocol command handlers.", release_notes)
            self.assertIn("Fixed blockers.", release_notes)

    def test_run_status_reports_current_phase_and_last_completed(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".arms").mkdir(parents=True)
            write_session(
                project_root,
                active_tasks=(
                    "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
                    "|---|------|----------------|--------------|--------------|--------|\n"
                    "| 1 | Fix: resolve API session expiry | arms-backend-agent | backend-system-architect | — | Pending |"
                ),
                completed_tasks="- Seed initial ARMS context",
                blockers="None",
            )

            output = self.invoke_cli(project_root, "--root", str(ARMS_ROOT), "run", "status")

            self.assertIn("**Current Phase:** Fix", output)
            self.assertIn("Fix: resolve API session expiry", output)
            self.assertIn("Seed initial ARMS context", output)


if __name__ == "__main__":
    unittest.main()
