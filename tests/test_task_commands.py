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
            memory_content = (project_root / ".arms" / "MEMORY.md").read_text(encoding="utf-8")
            self.assertIn("[PENDING APPROVAL][", memory_content)
            self.assertIn("Capture the reusable implementation decision behind 'Harden auth token validation'", memory_content)
            self.assertIn("Auto-memory draft staged", done_output)

    def test_task_log_accepts_agent_and_skill_aliases(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nTask aliases.\n", encoding="utf-8")
            self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))

            exit_code, output = self.invoke_cli(
                project_root,
                "task",
                "log",
                "--task",
                "Run regression audit on checkout flow",
                "--agent",
                "arms-qa-agent",
                "--skill",
                "qa-automation-testing",
                "--status",
                "In Progress",
                "--root",
                str(ARMS_ROOT),
            )

            self.assertEqual(exit_code, 0)
            session_content = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            self.assertIn("Run regression audit on checkout flow", session_content)
            self.assertIn("arms-qa-agent", session_content)
            self.assertIn("qa-automation-testing", session_content)
            self.assertIn("In Progress", output)

    def test_task_routing_uses_word_boundaries_for_keyword_matches(self):
        self.assertEqual(init_arms.infer_agent_from_task("Add API endpoint for auth"), "arms-backend-agent")
        self.assertEqual(init_arms.infer_agent_from_task("Add QA regression coverage"), "arms-qa-agent")
        self.assertEqual(init_arms.infer_agent_from_task("Review capital allocation memo"), "arms-main-agent")
        self.assertEqual(init_arms.infer_agent_from_task("Document attestation flow"), "arms-main-agent")

    def test_task_routing_realistic_phrasings_reach_specialists(self):
        expectations = {
            "Fix the broken login redirect after OAuth callback": "arms-backend-agent",
            "Add dark mode toggle to the settings screen": "arms-frontend-agent",
            "Set up GitHub Actions": "arms-devops-agent",
            "Make the dashboard look better": "arms-frontend-agent",
            "Add email notifications when an order ships": "arms-backend-agent",
            "Update the README with install steps": "arms-product-agent",
            "Create signup flow with magic links": "arms-backend-agent",
            "Audit our dependency versions for CVEs": "arms-security-agent",
            "Add rate limiting to prevent abuse": "arms-security-agent",
            "Migrate user table to add a phone column": "arms-data-agent",
            "Generate social preview images for sharing": "arms-media-agent",
            "Write unit tests for the parser": "arms-qa-agent",
        }
        for task_text, expected_agent in expectations.items():
            self.assertEqual(
                init_arms.infer_agent_from_task(task_text),
                expected_agent,
                msg="misrouted: {!r}".format(task_text),
            )

    def test_task_log_emits_delegation_handoff_for_specialist(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nDelegation handoff.\n", encoding="utf-8")
            self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))

            with mock.patch.dict(os.environ, {"ANTIGRAVITY_AGENT": "", "ANTIGRAVITY_CONVERSATION_ID": ""}):
                _, output = self.invoke_cli(
                    project_root,
                    "task",
                    "log",
                    "--root",
                    str(ARMS_ROOT),
                    "--task",
                    "Fix responsive layout breaking on tablets",
                )

            self.assertIn("Delegate to `arms-frontend-agent`", output)
            self.assertIn("model tier: `standard`", output)
            self.assertIn("Task tool", output)
            self.assertIn("/agent arms-frontend-agent", output)

    def test_render_delegation_hint_skips_main_agent(self):
        self.assertEqual(init_arms.render_delegation_hint("arms-main-agent", "power"), "")
        self.assertEqual(init_arms.render_delegation_hint("", ""), "")
        hint = init_arms.render_delegation_hint("arms-data-agent", "power")
        self.assertIn("arms-data-agent", hint)
        self.assertIn("model tier: `power`", hint)

    def test_render_delegation_hint_detects_cli_env(self):
        # Test Claude Code detection
        with mock.patch.dict(os.environ, {"CLAUDE_CODE": "1", "ANTIGRAVITY_AGENT": "", "ANTIGRAVITY_CONVERSATION_ID": ""}):
            hint = init_arms.render_delegation_hint("arms-frontend-agent", "standard")
            self.assertIn("Claude Code: run the `arms-frontend-agent` subagent via the Task tool", hint)
            self.assertNotIn("Copilot CLI", hint)

        # Test Antigravity detection
        with mock.patch.dict(os.environ, {"ANTIGRAVITY_AGENT": "1"}):
            hint = init_arms.render_delegation_hint("arms-frontend-agent", "standard", arms_root=str(ARMS_ROOT))
            self.assertIn("Antigravity: run the `arms-frontend-agent` subagent or switch the session", hint)
            self.assertIn("model: `gemini-flash-latest`", hint)
            self.assertNotIn("Claude Code", hint)

        # Test Codex detection via OPENAI_CODEX_CLI
        with mock.patch.dict(os.environ, {"OPENAI_CODEX_CLI": "1", "CLAUDE_CODE": "", "ANTIGRAVITY_AGENT": "", "ANTIGRAVITY_CONVERSATION_ID": ""}):
            hint = init_arms.render_delegation_hint("arms-frontend-agent", "standard", arms_root=str(ARMS_ROOT))
            self.assertIn("Codex CLI: switch the session to the `arms-frontend-agent` agent mirror", hint)
            self.assertIn("model: `gpt-5.4`", hint)
            self.assertNotIn("Claude Code", hint)

        # Test Codex detection via CODEX_THREAD_ID
        with mock.patch.dict(os.environ, {"CODEX_THREAD_ID": "123", "CLAUDE_CODE": "", "ANTIGRAVITY_AGENT": "", "ANTIGRAVITY_CONVERSATION_ID": ""}):
            hint = init_arms.render_delegation_hint("arms-frontend-agent", "standard", arms_root=str(ARMS_ROOT))
            self.assertIn("Codex CLI: switch the session to the `arms-frontend-agent` agent mirror", hint)
            self.assertIn("model: `gpt-5.4`", hint)
            self.assertNotIn("Claude Code", hint)

    def test_task_routing_ambiguous_tasks_stay_with_main_agent(self):
        # A single weak token overlap must not route away from the orchestrator.
        for task_text in (
            "Fix bug where saving a draft loses data",
            "Users report the app crashes on submit",
            "Optimize the slow search feature",
            "Refactor duplicate code in utils",
            "Improve error messages shown to users",
        ):
            self.assertEqual(
                init_arms.infer_agent_from_task(task_text),
                "arms-main-agent",
                msg="over-routed: {!r}".format(task_text),
            )

    def test_task_update_blocked_auto_stages_memory_once(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nBlocked task memory.\n", encoding="utf-8")
            self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))

            _, log_output = self.invoke_cli(
                project_root,
                "task",
                "log",
                "--task",
                "Fix auth token refresh race on mobile",
                "--root",
                str(ARMS_ROOT),
            )
            task_id = re.search(r"Task ID: `([^`]+)`", log_output).group(1)

            exit_code, first_update = self.invoke_cli(
                project_root,
                "task",
                "update",
                "--task-id",
                task_id,
                "--status",
                "Blocked",
                "--root",
                str(ARMS_ROOT),
            )
            self.assertEqual(exit_code, 0)
            self.assertIn("Auto-memory draft staged", first_update)

            exit_code, second_update = self.invoke_cli(
                project_root,
                "task",
                "update",
                "--task-id",
                task_id,
                "--status",
                "Blocked",
                "--root",
                str(ARMS_ROOT),
            )
            self.assertEqual(exit_code, 0)
            self.assertIn("Auto-memory draft already pending", second_update)

            memory_content = (project_root / ".arms" / "MEMORY.md").read_text(encoding="utf-8")
            self.assertEqual(
                memory_content.count("Document the root cause and final resolution for 'Fix auth token refresh race on mobile'"),
                1,
            )


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
