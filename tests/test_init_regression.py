import io
import os
import sys
import threading
import time
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


class InitRegressionTests(unittest.TestCase):
    def invoke_cli(self, cwd, *args):
        stdout = io.StringIO()
        with working_directory(cwd), mock.patch.object(sys, "argv", ["arms", *args]), redirect_stdout(stdout):
            init_arms.main()
        return stdout.getvalue()

    def test_init_from_nested_directory_uses_legacy_parent_project_root(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "timefirst"
            nested_dir = project_root / "app"
            nested_dir.mkdir(parents=True)

            (project_root / "session.md").write_text("# old session\n", encoding="utf-8")
            (project_root / "rules.md").write_text("# old rules\n", encoding="utf-8")
            root_gemini_path = project_root / "gemini.md"
            root_gemini_path.write_text("# Project instructions\nUse the existing architecture.\n", encoding="utf-8")
            (project_root / "agents.yaml").write_text("agents:\n", encoding="utf-8")

            self.invoke_cli(nested_dir, "init", "yolo", "--root", str(ARMS_ROOT))

            self.assertTrue((project_root / ".arms" / "SESSION.md").exists())
            self.assertTrue((project_root / ".arms" / "ENGINE.md").exists())
            self.assertTrue((project_root / ".arms" / "RULES.md").exists())
            self.assertFalse((project_root / ".gemini" / "GEMINI.md").exists())
            self.assertFalse((project_root / ".gemini" / "RULES.md").exists())
            self.assertFalse((project_root / "session.md").exists())
            self.assertFalse((project_root / "rules.md").exists())

            root_gemini = root_gemini_path.read_text(encoding="utf-8")
            self.assertEqual(root_gemini, "# Project instructions\nUse the existing architecture.\n")
            engine_instructions = (project_root / ".arms" / "ENGINE.md").read_text(encoding="utf-8")
            migrated_rules = (project_root / ".arms" / "RULES.md").read_text(encoding="utf-8")
            self.assertIn("Strict Init Rule", engine_instructions)
            self.assertEqual(migrated_rules, "# old rules\n")

    def test_sync_engine_instructions_preserves_root_gemini(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".arms").mkdir()
            root_gemini_path = project_root / "GEMINI.md"
            root_gemini_path.write_text("# Project-specific Gemini instructions\n", encoding="utf-8")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                init_arms.sync_engine_instructions(str(ARMS_ROOT), str(project_root))

            engine_instructions = (project_root / ".arms" / "ENGINE.md").read_text(encoding="utf-8")
            root_gemini = root_gemini_path.read_text(encoding="utf-8")

            self.assertIn("Strict Init Rule", engine_instructions)
            self.assertEqual(root_gemini, "# Project-specific Gemini instructions\n")

    def test_infer_brand_context_reads_gemini_from_gemini_directory(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".gemini").mkdir()
            (project_root / ".gemini" / "GEMINI.md").write_text(
                "# Project Notes\nThis system coordinates campus attendance workflows.\n",
                encoding="utf-8",
            )

            inferred = init_arms.infer_brand_context_from_project(str(project_root))

            self.assertEqual(inferred["mission"], "This system coordinates campus attendance workflows.")

    def test_run_init_once_restores_engine_version_in_session(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".arms").mkdir()
            (project_root / ".gemini").mkdir()

            session_content = """# ARMS Session Log
Generated: old

## Environment
- ARMS Root: /tmp/fake
- Project Root: {root}
- Project Name: Demo
- Execution Mode: Parallel
- YOLO Mode: Disabled

## Active Agents
- arms-main-agent

## Active Skills
- arms-orchestrator [Active]

## Active Tasks
| # | Task | Assigned Agent | Active Skill | Dependencies | Status |
|---|------|----------------|--------------|--------------|--------|
| 1 | Existing task | arms-main-agent | arms-orchestrator | None | Pending |

## Completed Tasks
- None

## Blockers
None
""".format(root=project_root)
            (project_root / ".arms" / "SESSION.md").write_text(session_content, encoding="utf-8")
            (project_root / ".arms" / "BRAND.md").write_text(
                "# Brand Context\n- **Project Name:** Demo\n- **Mission:** Ship useful software\n",
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                init_arms.run_init_once(
                    str(project_root),
                    str(ARMS_ROOT),
                    "init yolo",
                    True,
                    show_banner=False,
                )

            updated_session = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            self.assertIn(f"- Engine Version: {init_arms.__version__}", updated_session)
            self.assertIn("| 1 | Existing task | arms-main-agent | arms-orchestrator | None | Pending |", updated_session)

    def test_wait_for_brand_change_returns_after_file_update(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".arms").mkdir()
            brand_path = project_root / ".arms" / "BRAND.md"
            brand_path.write_text("initial", encoding="utf-8")
            signature = init_arms.capture_file_signature(str(brand_path))

            def mutate_brand():
                time.sleep(0.05)
                brand_path.write_text("updated", encoding="utf-8")

            watcher_output = io.StringIO()
            worker = threading.Thread(target=mutate_brand)
            with mock.patch.object(init_arms, "WATCH_POLL_INTERVAL_SECONDS", 0.01), redirect_stdout(watcher_output):
                worker.start()
                init_arms.wait_for_brand_change(str(project_root), signature)
                worker.join()

            self.assertIn("Detected BRAND.md change", watcher_output.getvalue())

    def test_parse_structured_answers_maps_stack_shortcuts(self):
        answers = init_arms.parse_structured_answers(
            "11. A\n12. 1\nPreferred tech stack: B\nDeployment target: 2\n"
        )

        self.assertEqual(
            answers["Preferred Tech Stack"],
            "Nuxt + Firebase + Nuxt UI (latest stable)",
        )
        self.assertEqual(answers["Deployment Target"], "Docker / VPS")

    def test_resolve_stack_recommendation_prefers_astro_for_content_sites(self):
        profile = init_arms.resolve_stack_recommendation(
            {
                "Preferred Tech Stack": "Custom",
                "Primary Use Case": "Content/Marketing",
                "Project Type": "Content / Marketing Site",
                "Experience Type": "Editorial",
                "Technical Constraints": "Readable typography and strong SEO",
                "Backend / Data Layer": "",
                "Deployment Target": "",
                "Authentication Requirement": "",
                "Required Website Sections": "Header/Nav, Hero, Featured Content, Footer",
                "SEO Focus": "Informational search",
            }
        )

        self.assertEqual(profile["key"], "astro")
        self.assertEqual(profile["ui_system"], "DaisyUI")
        self.assertTrue(profile["inferred"])

    def test_new_project_answers_generate_context_synthesis_prompts_and_seeded_tasks(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            answers = "\n".join(
                [
                    "Project Name: OrbitOps",
                    "Mission: Help operations teams automate approvals and audits.",
                    "Vision: Become the operating layer for internal workflow automation.",
                    "Personality: Technical, sharp, trustworthy",
                    "Primary Audience: Operations and RevOps teams",
                    "Core Values: Clarity, reliability, speed",
                    "Differentiation: Faster setup and clearer audit trails than legacy tools",
                    "Color Palette: Slate, indigo, white",
                    "Typography: Geist UI with Inter body text",
                    "1. SaaS",
                    "2. Operations and RevOps teams",
                    "3. Approval routing, audit trails, analytics dashboards",
                    "4. B2B subscription",
                    "7. Linear",
                    "8. Like Linear but warmer",
                    "9. Logo (N) · Color palette (Y) · Typography (Y) · Existing site (N)",
                    "10. Dark",
                    "11. A",
                    "12. 1",
                    "13. Supabase",
                    "14. OAuth",
                    "15. TypeScript only, Tailwind required",
                    "16. Marketing site",
                    "17. Workflow automation SaaS",
                    "18. Worldwide",
                    "19. Header/Nav, Hero, Features, Pricing, CTA, Footer",
                    "20. Start Free, Book Demo",
                    "21. Lucide",
                    "22. Dashboard mockups and hero image",
                    "23. Workflow automation, audit trail, team approvals",
                    "24. No emoji",
                ]
            )

            result = init_arms.run_init_once(
                str(project_root),
                str(ARMS_ROOT),
                "init",
                False,
                preset_name="saas",
                answers_text=answers,
                show_banner=False,
            )

            synthesis = (project_root / ".arms" / "CONTEXT_SYNTHESIS.md").read_text(encoding="utf-8")
            prompts = (project_root / ".arms" / "GENERATED_PROMPTS.md").read_text(encoding="utf-8")
            session = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")

            self.assertEqual(result["status"], "complete")
            self.assertIn("**UI System:** shadcn/ui", synthesis)
            self.assertIn("**Recommended Stack:** Next.js + Supabase + shadcn/ui", synthesis)
            self.assertIn("Read `.arms/CONTEXT_SYNTHESIS.md` first", prompts)
            self.assertIn("shadcn/ui", prompts)
            self.assertIn("nano-banana-pro", prompts)
            self.assertIn("Generate at least five production-ready images", prompts)
            self.assertIn("showcase their best work", prompts)
            self.assertIn("| 1 | Create a concise product charter, scope summary, and success metrics |", session)
            self.assertIn("Nano Banana landing-page imagery", session)
            self.assertIn("arms-devops-agent", session)
            self.assertIn("devops-orchestrator", session)


if __name__ == "__main__":
    unittest.main()
