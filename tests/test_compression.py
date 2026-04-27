import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from arms_engine import compression as compression_module
from arms_engine import init_arms
from arms_engine import session as session_module


REPO_ROOT = Path(__file__).resolve().parents[1]
ARMS_ROOT = REPO_ROOT / "arms_engine"


def write_session(project_root, active_tasks, completed_tasks="- None", blockers="None"):
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
- arms-backend-agent

## Active Skills
- arms-orchestrator [Active]
- backend-system-architect

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
        active_tasks=active_tasks,
        completed_tasks=completed_tasks,
        blockers=blockers,
    )
    (project_root / ".arms" / "SESSION.md").write_text(session_content, encoding="utf-8")


class CompressionTests(unittest.TestCase):
    def test_compress_workspace_archives_done_tasks_and_compacts_memory(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".arms").mkdir()
            write_session(
                project_root,
                active_tasks=(
                    "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
                    "|---|------|----------------|--------------|--------------|--------|\n"
                    "| 1 | Ship release checklist | arms-main-agent | arms-orchestrator | — | Done |\n"
                    "| 2 | Patch API session expiry | arms-backend-agent | backend-system-architect | — | In Progress |\n"
                    "| 3 | Wait for security sign-off | arms-main-agent | arms-orchestrator | — | Blocked |"
                ),
                completed_tasks="- Documented rollout notes\n- Shared handoff summary",
            )
            (project_root / ".arms" / "MEMORY.md").write_text(
                """# ARMS Project Memory

> Managed by ARMS Engine. This is a continuous learning file. APPEND only; never overwrite.

## Project Context & MVP
- Decision: Use Next.js + Supabase for the control plane

## Known Bugs & Fixes
- Auth expiry check: use <= comparison for expired tokens
""",
                encoding="utf-8",
            )

            summary = compression_module.compress_workspace(str(project_root))

            session = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            archive = (project_root / ".arms" / "SESSION_ARCHIVE.md").read_text(encoding="utf-8")
            memory = (project_root / ".arms" / "MEMORY.md").read_text(encoding="utf-8")

            self.assertEqual(summary["archived_tasks"], 1)
            self.assertEqual(summary["archived_notes"], 2)
            self.assertIn("Patch API session expiry", session)
            self.assertIn("Wait for security sign-off", session)
            self.assertNotIn("Ship release checklist", session)
            self.assertIn("## Completed Tasks", session)
            self.assertIn("- None", session)
            self.assertIn("Compression pass", archive)
            self.assertIn("Ship release checklist", archive)
            self.assertIn("Documented rollout notes", archive)
            self.assertIn("[PROJECT CONTEXT & MVP] :", memory)
            self.assertIn("Next.js + Supabase", memory)
            self.assertIn("[KNOWN BUGS & FIXES] :", memory)
            self.assertIn("<= comparison", memory)

    def test_maintain_archive_summary_writes_history_summary_when_threshold_exceeded(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".arms").mkdir()
            archive_content = """# ARMS Session Archive

> Managed by ARMS Engine. Append completed or cancelled work here; never delete history.

## Archive — 2026-04-20T00:00:00Z
### Context: First pass

| # | Task | Agent | Status | Completed |
|---|------|-------|--------|-----------|
| 1 | Old task | arms-main-agent | Done | 2026-04-20T00:00:00Z |

### Completed Notes
- very long note repeated many times very long note repeated many times very long note repeated many times

## Archive — 2026-04-26T00:00:00Z
### Context: Latest pass

| # | Task | Agent | Status | Completed |
|---|------|-------|--------|-----------|
| 1 | Recent task | arms-main-agent | Done | 2026-04-26T00:00:00Z |
"""
            (project_root / ".arms" / "SESSION_ARCHIVE.md").write_text(archive_content, encoding="utf-8")

            with mock.patch.object(compression_module, "ARCHIVE_TOKEN_LIMIT", 10):
                result = compression_module.maintain_archive_summary(str(project_root))

            history_summary = (project_root / ".arms" / "HISTORY_SUMMARY.md").read_text(encoding="utf-8")
            self.assertTrue(result["updated"])
            self.assertIn("First pass", history_summary)
            self.assertIn("1 task(s)", history_summary)

    def test_run_init_once_compress_executes_real_compression_flow(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".arms").mkdir()
            (project_root / ".gemini").mkdir()
            (project_root / ".arms" / "BRAND.md").write_text(
                """# Brand Context
- **Project Name:** Demo
- **Mission:** Keep orchestration compact.
- **Vision:** Reduce state sprawl.
- **Personality:** Direct
- **Voice & Tone:** Clear
- **Primary Audience:** Builders
- **Core Values:** Clarity
- **Differentiation:** Persistent execution
- **Color Palette:** Slate
- **Typography:** Inter
- **Logo Status:** Existing asset detected
- **Visual Direction:** Dark
- **Project Type:** Web Application
- **Design Priority:** Product clarity
- **Preferred Tech Stack:** Next.js + Supabase + shadcn/ui (latest stable)
- **Deployment Target:** Vercel
- **Backend / Data Layer:** Supabase
- **Authentication Requirement:** OAuth
- **Technical Constraints:** TypeScript only
- **Experience Type:** App shell
- **Industry / Business Niche:** SaaS
- **Service Area / Local SEO Target:** Worldwide
- **Required Website Sections:** Header/Nav, Hero, Footer
- **Primary Calls to Action:** Start
- **Icon System:** Lucide
- **Image Requirements:** Minimal
- **SEO Focus:** Workflow automation
""",
                encoding="utf-8",
            )
            write_session(
                project_root,
                active_tasks=(
                    "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
                    "|---|------|----------------|--------------|--------------|--------|\n"
                    "| 1 | Completed setup task | arms-main-agent | arms-orchestrator | — | Done |\n"
                    "| 2 | Remaining setup task | arms-main-agent | arms-orchestrator | — | Pending |"
                ),
            )
            (project_root / ".arms" / "MEMORY.md").write_text(session_module.MEMORY_TEMPLATE, encoding="utf-8")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = init_arms.run_init_once(
                    str(project_root),
                    str(ARMS_ROOT),
                    "init compress",
                    False,
                    show_banner=False,
                )

            session = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            archive = (project_root / ".arms" / "SESSION_ARCHIVE.md").read_text(encoding="utf-8")
            output = stdout.getvalue()

            self.assertEqual(result["status"], "complete")
            self.assertIn("Compression complete.", output)
            self.assertNotIn("stub activated", output)
            self.assertIn("Completed setup task", archive)
            self.assertNotIn("Completed setup task", session)
            self.assertIn("Remaining setup task", session)


if __name__ == "__main__":
    unittest.main()
