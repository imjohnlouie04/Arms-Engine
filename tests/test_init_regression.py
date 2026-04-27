import io
import os
import shutil
import subprocess
import sys
import threading
import time
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from arms_engine import init_arms
from arms_engine import cli as cli_module
from arms_engine import session as session_module
from arms_engine import versioning as versioning_module


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

    def test_infer_brand_context_reads_project_copilot_instructions(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".github").mkdir()
            (project_root / ".github" / "copilot-instructions.md").write_text(
                "# Repository Notes\nThis platform helps clinics coordinate same-day patient scheduling.\n",
                encoding="utf-8",
            )

            inferred = init_arms.infer_brand_context_from_project(str(project_root))

            self.assertEqual(inferred["mission"], "This platform helps clinics coordinate same-day patient scheduling.")

    def test_init_preserves_project_copilot_instructions(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".github").mkdir()
            instructions_path = project_root / ".github" / "copilot-instructions.md"
            instructions_path.write_text(
                "# Project instructions\nKeep the existing deployment workflow.\n",
                encoding="utf-8",
            )
            (project_root / "README.md").write_text(
                "# Scheduler\nClinic scheduling platform.\n",
                encoding="utf-8",
            )

            self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))

            self.assertEqual(
                instructions_path.read_text(encoding="utf-8"),
                "# Project instructions\nKeep the existing deployment workflow.\n",
            )
            self.assertTrue((project_root / "AGENTS.md").exists())

    def test_python_module_entrypoint_runs_init(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nModule entrypoint.\n", encoding="utf-8")

            env = os.environ.copy()
            existing_pythonpath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = (
                str(REPO_ROOT)
                if not existing_pythonpath
                else f"{REPO_ROOT}{os.pathsep}{existing_pythonpath}"
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "arms_engine.init_arms",
                    "init",
                    "yolo",
                    "--root",
                    str(ARMS_ROOT),
                ],
                cwd=project_root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}",
            )
            self.assertIn("Initializing ARMS Engine", result.stdout)
            self.assertTrue((project_root / ".arms" / "SESSION.md").exists())

    def test_init_arms_shell_script_preserves_pythonpath_and_runs_init(self):
        with TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            project_root = temp_root / "project"
            helper_dir = temp_root / "pythonpath-helper"
            marker_path = temp_root / "sitecustomize-loaded.txt"
            project_root.mkdir()
            helper_dir.mkdir()
            (project_root / "README.md").write_text("# Demo\nShell linker.\n", encoding="utf-8")
            (helper_dir / "sitecustomize.py").write_text(
                "import os\n"
                "marker = os.environ.get('ARMS_TEST_SITECUSTOMIZE_MARKER')\n"
                "if marker:\n"
                "    with open(marker, 'w', encoding='utf-8') as f:\n"
                "        f.write('loaded')\n",
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["PYTHONPATH"] = str(helper_dir)
            env["ARMS_TEST_SITECUSTOMIZE_MARKER"] = str(marker_path)

            result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "init-arms.sh"),
                    "init",
                    "yolo",
                    "--root",
                    str(REPO_ROOT),
                ],
                cwd=project_root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}",
            )
            self.assertTrue(marker_path.exists(), msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            self.assertIn("Initializing ARMS Engine", result.stdout)
            self.assertTrue((project_root / ".arms" / "SESSION.md").exists())

    def test_init_syncs_memory_approval_gate_into_gemini_agent_and_engine_instructions(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nMemory approval sync.\n", encoding="utf-8")

            self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))

            gemini_agent = (project_root / ".gemini" / "agents" / "arms-main-agent.md").read_text(encoding="utf-8")
            engine_instructions = (project_root / ".arms" / "ENGINE.md").read_text(encoding="utf-8")
            rules = (project_root / ".arms" / "RULES.md").read_text(encoding="utf-8")

            self.assertIn("Must ask for explicit user approval before updating `.arms/MEMORY.md`.", gemini_agent)
            self.assertIn("Before appending to or editing `.arms/MEMORY.md`, ask the user explicitly.", engine_instructions)
            self.assertIn("Ask the user for approval before updating `.arms/MEMORY.md`", rules)

    def test_init_injects_agents_yaml_rules_into_mirrored_agent_markdown(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nAgent rule sync.\n", encoding="utf-8")

            self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))

            gemini_data_agent = (project_root / ".gemini" / "agents" / "arms-data-agent.md").read_text(encoding="utf-8")
            github_data_agent = (project_root / ".github" / "agents" / "arms-data-agent.md").read_text(encoding="utf-8")

            expected_rule = "Must use Supabase CLI (supabase init / supabase start) local environment for all schema tests before remote execution."
            self.assertIn("## Runtime Rules", gemini_data_agent)
            self.assertIn(expected_rule, gemini_data_agent)
            self.assertIn(expected_rule, github_data_agent)

    def test_reinit_prunes_stale_agent_mirror_files(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nAgent prune sync.\n", encoding="utf-8")

            self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))

            stale_gemini = project_root / ".gemini" / "agents" / "stale-agent.md"
            stale_github = project_root / ".github" / "agents" / "stale-agent.md"
            stale_gemini.write_text("# stale\n", encoding="utf-8")
            stale_github.write_text("# stale\n", encoding="utf-8")

            self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))

            self.assertFalse(stale_gemini.exists())
            self.assertFalse(stale_github.exists())

    def test_init_syncs_explicit_skill_binding_from_agents_yaml(self):
        with TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            engine_root = temp_root / "engine"
            project_root = temp_root / "project"
            shutil.copytree(ARMS_ROOT, engine_root)
            project_root.mkdir()

            skill_dir = engine_root / "skills" / "supabase"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "\n".join(
                    [
                        "---",
                        "name: supabase",
                        "description: Use for Supabase database auth RLS schema changes and storage.",
                        "---",
                        "",
                        "# Supabase",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            agents_yaml_path = engine_root / "agents.yaml"
            agents_yaml_path.write_text(
                agents_yaml_path.read_text(encoding="utf-8").replace(
                    "  arms-data-agent:\n    role: Data Specialist\n    scope: Schema design, migrations, query optimization.\n",
                    "  arms-data-agent:\n    role: Data Specialist\n    scope: Schema design, migrations, query optimization.\n    skills:\n      - supabase\n",
                ),
                encoding="utf-8",
            )

            self.invoke_cli(project_root, "init", "yolo", "--root", str(engine_root))

            registry = init_arms.load_agents_registry(str(project_root / ".gemini"))
            registry_by_name = {agent["name"]: agent for agent in registry}
            self.assertIn("supabase", registry_by_name["arms-data-agent"]["skills"])

            session_content = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            self.assertIn("- arms-data-agent (supabase)", session_content)
            self.assertTrue((project_root / ".agents" / "skills" / "supabase" / "SKILL.md").exists())
            self.assertTrue((project_root / ".gemini" / "skills" / "supabase" / "SKILL.md").exists())
            self.assertTrue((project_root / ".github" / "skills" / "supabase" / "SKILL.md").exists())
            self.assertIn("supabase:", (project_root / ".agents" / "skills.yaml").read_text(encoding="utf-8"))
            self.assertIn("supabase:", (project_root / ".gemini" / "skills.yaml").read_text(encoding="utf-8"))
            self.assertIn("supabase:", (project_root / ".github" / "skills.yaml").read_text(encoding="utf-8"))
            self.assertIn(".gemini/skills/arms-orchestrator/SKILL.md", (project_root / ".gemini" / "skills-index.md").read_text(encoding="utf-8"))

    def test_init_syncs_all_engine_skills_to_all_skill_mirrors(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nSkill mirror sync.\n", encoding="utf-8")

            self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))

            expected_skills = {
                path.name
                for path in (ARMS_ROOT / "skills").iterdir()
                if path.is_dir() and (path / "SKILL.md").exists()
            }
            for relative_root in (".agents/skills", ".gemini/skills", ".github/skills"):
                mirror_root = project_root / relative_root
                mirrored_skills = {path.name for path in mirror_root.iterdir() if path.is_dir()}
                self.assertEqual(mirrored_skills, expected_skills)
            for relative_file in (
                ".agents/skills.yaml",
                ".agents/skills-index.md",
                ".gemini/skills.yaml",
                ".gemini/skills-index.md",
                ".github/skills.yaml",
                ".github/skills-index.md",
            ):
                self.assertTrue((project_root / relative_file).exists())

    def test_reinit_existing_project_refreshes_skill_mirrors_and_registries(self):
        with TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            engine_root = temp_root / "engine"
            project_root = temp_root / "project"
            shutil.copytree(ARMS_ROOT, engine_root)
            project_root.mkdir()
            (project_root / "README.md").write_text("# Demo\nExisting project.\n", encoding="utf-8")

            self.invoke_cli(project_root, "init", "yolo", "--root", str(engine_root))

            skill_dir = engine_root / "skills" / "supabase"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "\n".join(
                    [
                        "---",
                        "name: supabase",
                        "description: Use for Supabase database auth RLS schema changes and storage.",
                        "---",
                        "",
                        "# Supabase",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            agents_yaml_path = engine_root / "agents.yaml"
            agents_yaml_path.write_text(
                agents_yaml_path.read_text(encoding="utf-8").replace(
                    "  arms-data-agent:\n    role: Data Specialist\n    scope: Schema design, migrations, query optimization.\n",
                    "  arms-data-agent:\n    role: Data Specialist\n    scope: Schema design, migrations, query optimization.\n    skills:\n      - supabase\n",
                ),
                encoding="utf-8",
            )

            self.invoke_cli(project_root, "init", "yolo", "--root", str(engine_root))

            for relative_root in (".agents/skills", ".gemini/skills", ".github/skills"):
                self.assertTrue((project_root / relative_root / "supabase" / "SKILL.md").exists())
            for relative_file in (
                ".agents/skills.yaml",
                ".gemini/skills.yaml",
                ".github/skills.yaml",
                ".agents/skills-index.md",
                ".gemini/skills-index.md",
                ".github/skills-index.md",
            ):
                self.assertIn("supabase", (project_root / relative_file).read_text(encoding="utf-8"))

    def test_resolve_agents_with_skills_uses_only_agents_yaml_bindings(self):
        with TemporaryDirectory() as tmp:
            engine_root = Path(tmp) / "engine"
            shutil.copytree(ARMS_ROOT, engine_root)

            skill_dir = engine_root / "skills" / "platform-ops"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "\n".join(
                    [
                        "---",
                        "name: platform-ops",
                        "description: Guidance for releases, environments, and cloud operations.",
                        "agent: arms-devops-agent",
                        "---",
                        "",
                        "# Platform Ops",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            agents, _, inferred = init_arms.resolve_agents_with_skills(str(engine_root), announce=False)
            bindings = {agent["name"]: agent.get("skills", []) for agent in agents}

            self.assertEqual(inferred, [])
            self.assertNotIn("platform-ops", bindings["arms-devops-agent"])

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

    def test_parse_structured_answers_handles_mixed_formats_and_continuations(self):
        answers = init_arms.parse_structured_answers(
            "\n".join(
                [
                    "- **Mission:** Build approvals that stay auditable",
                    "without adding operational drag.",
                    "11. Preferred tech stack: A",
                    "Deployment Target: 3",
                    "Technical Constraints: TypeScript only",
                    "Tailwind required",
                ]
            )
        )

        self.assertEqual(
            answers["Mission"],
            "Build approvals that stay auditable without adding operational drag.",
        )
        self.assertEqual(
            answers["Preferred Tech Stack"],
            "Next.js + Supabase + shadcn/ui (latest stable)",
        )
        self.assertEqual(answers["Deployment Target"], "AWS / GCP")
        self.assertEqual(
            answers["Technical Constraints"],
            "TypeScript only Tailwind required",
        )

    def test_format_git_describe_version_handles_exact_tags_commits_and_dirty_state(self):
        self.assertEqual(init_arms.format_git_describe_version("v1.5.0"), "1.5.0")
        self.assertEqual(
            init_arms.format_git_describe_version("v1.5.0-3-gabc1234"),
            "1.5.0.dev3+gabc1234",
        )
        self.assertEqual(
            init_arms.format_git_describe_version("v1.5.0-dirty"),
            "1.5.0+dirty",
        )

    def test_format_git_describe_version_handles_bare_commit_hash(self):
        result = versioning_module.format_git_describe_version("abc1234")
        self.assertEqual(result, "0.0.0.dev0+gabc1234")

    def test_read_version_file_reads_generated_module_without_package_import(self):
        with TemporaryDirectory() as tmp:
            version_file = Path(tmp) / "_version.py"
            version_file.write_text("__version__ = version = '9.9.9'\n", encoding="utf-8")

            self.assertEqual(versioning_module._read_version_file(tmp), "9.9.9")

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

    def test_migrate_legacy_state_handles_move_keep_and_missing_cases(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "move-case"
            (project_root / ".arms").mkdir(parents=True)
            legacy_session = project_root / "session.md"
            legacy_session.write_text("# legacy session\n", encoding="utf-8")

            init_arms.migrate_legacy_state(str(project_root))

            self.assertFalse(legacy_session.exists())
            self.assertEqual(
                (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8"),
                "# legacy session\n",
            )

        with TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "keep-case"
            (project_root / ".arms").mkdir(parents=True)
            legacy_session = project_root / "session.md"
            target_session = project_root / ".arms" / "SESSION.md"
            legacy_session.write_text("# legacy session\n", encoding="utf-8")
            target_session.write_text("# existing session\n", encoding="utf-8")

            init_arms.migrate_legacy_state(str(project_root))

            self.assertTrue(legacy_session.exists())
            self.assertEqual(target_session.read_text(encoding="utf-8"), "# existing session\n")

        with TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "missing-case"
            (project_root / ".arms").mkdir(parents=True)

            init_arms.migrate_legacy_state(str(project_root))

            self.assertFalse((project_root / ".arms" / "SESSION.md").exists())

    def test_brand_file_requires_bootstrap_distinguishes_empty_placeholder_and_complete_briefs(self):
        self.assertTrue(init_arms.brand_file_requires_bootstrap(""))
        self.assertTrue(init_arms.brand_file_requires_bootstrap("# Brand Context\n- **Mission:** [Purpose]\n"))

        incomplete_questionnaire = init_arms.render_new_project_brand_questionnaire("/tmp/demo")
        self.assertTrue(init_arms.brand_file_requires_bootstrap(incomplete_questionnaire))

        complete_brand = """# Brand Context
- **Project Name:** OrbitOps
- **Mission:** Help teams automate approvals.
- **Vision:** Become the operating layer for workflow automation.
- **Personality:** Technical, trustworthy
- **Voice & Tone:** Clear and direct
- **Primary Audience:** Operations teams
- **Core Values:** Clarity, reliability
- **Differentiation:** Faster setup than legacy tools
- **Color Palette:** Slate, indigo, white
- **Typography:** Geist + Inter
- **Logo Status:** Existing asset detected
- **Visual Direction:** Dark
- **Project Type:** Web Application
- **Design Priority:** Product clarity
- **Preferred Tech Stack:** Next.js + Supabase + shadcn/ui (latest stable)
- **Deployment Target:** Vercel
- **Backend / Data Layer:** Supabase
- **Authentication Requirement:** OAuth
- **Technical Constraints:** TypeScript only
- **Experience Type:** Marketing site
- **Industry / Business Niche:** SaaS
- **Service Area / Local SEO Target:** Worldwide
- **Required Website Sections:** Header/Nav, Hero, Features, CTA, Footer
- **Primary Calls to Action:** Start Free
- **Icon System:** Lucide
- **Image Requirements:** 5+ images
- **SEO Focus:** Workflow automation
"""
        self.assertFalse(init_arms.brand_file_requires_bootstrap(complete_brand))

    def test_apply_answers_to_brand_content_round_trip_updates_direct_derived_and_note_fields(self):
        with TemporaryDirectory() as tmp:
            content = init_arms.render_new_project_brand_questionnaire(tmp)
            updated_content, summary = init_arms.apply_answers_to_brand_content(
                content,
                {
                    "Project Name": "OrbitOps",
                    "Mission": "Help operations teams automate approvals.",
                    "Primary Use Case": "SaaS",
                    "Brand Comparison": "Like Linear but warmer",
                    "Existing Brand Assets": "Logo (N) · Color palette (Y)",
                    "Content / Visual Non-Negotiables": "No emoji",
                },
            )

            self.assertIn("- **Project Name:** OrbitOps", updated_content)
            self.assertIn("- **Mission:** Help operations teams automate approvals.", updated_content)
            self.assertIn("- **Project Type:** Web Application", updated_content)
            self.assertIn("- **Differentiation:** Like Linear but warmer", updated_content)
            self.assertIn("- **Logo Status:** Not yet created", updated_content)
            self.assertIn("- **Technical Constraints:** No emoji", updated_content)
            self.assertIn("- Primary Use Case: SaaS", updated_content)
            self.assertIn("- Brand Comparison: Like Linear but warmer", updated_content)
            self.assertIn("- Existing Brand Assets: Logo (N) · Color palette (Y)", updated_content)
            self.assertIn("- Content / Visual Non-Negotiables: No emoji", updated_content)
            self.assertIn("Project Name", summary["fields"])
            self.assertIn("Primary Use Case", summary["notes"])

    def test_update_session_preserves_existing_valid_tasks_and_uses_atomic_write(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".arms").mkdir()
            (project_root / ".arms" / "BRAND.md").write_text(
                "# Brand Context\n- **Project Name:** Demo\n",
                encoding="utf-8",
            )
            (project_root / ".arms" / "SESSION.md").write_text(
                """# ARMS Session Log
Generated: old

## Environment
- ARMS Root: /tmp/fake
- Engine Version: 1.0.0
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
""".format(root=project_root),
                encoding="utf-8",
            )

            with mock.patch.object(session_module, "write_text_atomic", wraps=session_module.write_text_atomic) as atomic_write:
                updated = init_arms.update_session(
                    str(project_root),
                    str(ARMS_ROOT),
                    "- arms-orchestrator [Active]",
                    "- arms-main-agent",
                    startup_tasks_content=(
                        "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
                        "|---|------|----------------|--------------|--------------|--------|\n"
                        "| 1 | Seeded task | arms-main-agent | arms-orchestrator | — | Pending |"
                    ),
                )

            self.assertTrue(updated)
            atomic_write.assert_called_once()
            session_content = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            self.assertIn("| 1 | Existing task | arms-main-agent | arms-orchestrator | None | Pending |", session_content)
            self.assertNotIn("Seeded task", session_content)
            self.assertIn(f"- Engine Version: {init_arms.__version__}", session_content)

    def test_update_session_falls_back_to_existing_session_name_when_brand_name_is_missing(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".arms").mkdir()
            (project_root / ".arms" / "BRAND.md").write_text(
                "# Brand Context\n- **Mission:** Ship useful software\n",
                encoding="utf-8",
            )
            (project_root / ".arms" / "SESSION.md").write_text(
                """# ARMS Session Log
Generated: old

## Environment
- ARMS Root: /tmp/fake
- Engine Version: 1.0.0
- Project Root: {root}
- Project Name: Preserved Demo
- Execution Mode: Parallel
- YOLO Mode: Disabled

## Active Agents
- arms-main-agent

## Active Skills
- arms-orchestrator [Active]

## Active Tasks
| # | Task | Assigned Agent | Active Skill | Dependencies | Status |
|---|------|----------------|--------------|--------------|--------|

## Completed Tasks
- None

## Blockers
None
""".format(root=project_root),
                encoding="utf-8",
            )

            init_arms.update_session(
                str(project_root),
                str(ARMS_ROOT),
                "- arms-orchestrator [Active]",
                "- arms-main-agent",
            )

            session_content = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            self.assertIn("- Project Name: Preserved Demo", session_content)

    def test_update_session_infers_project_name_when_brand_is_missing(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "discipleship-community"
            project_root.mkdir()
            (project_root / ".arms").mkdir()
            (project_root / "package.json").write_text(
                '{"name":"discipleship-community","description":"A community platform."}',
                encoding="utf-8",
            )

            init_arms.update_session(
                str(project_root),
                str(ARMS_ROOT),
                "- arms-orchestrator [Active]",
                "- arms-main-agent",
            )

            session_content = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            self.assertIn("- Project Name: discipleship-community", session_content)

    def test_is_development_engine_requires_dev_or_local_version_marker(self):
        with mock.patch.object(session_module, "__version__", "1.5.0"):
            self.assertFalse(init_arms.is_development_engine(str(ARMS_ROOT)))

        with mock.patch.object(session_module, "__version__", "1.5.1.dev2+g123"):
            self.assertTrue(init_arms.is_development_engine(str(ARMS_ROOT)))

        with mock.patch.object(session_module, "__version__", "abc1234"):
            self.assertTrue(init_arms.is_development_engine(str(ARMS_ROOT)))

    def test_engine_version_guard_suggests_local_checkout_rerun_when_available(self):
        with TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            project_root = temp_root / "project"
            checkout_root = temp_root / "Arms-Engine"
            checkout_package_dir = checkout_root / "arms_engine"
            project_root.mkdir()
            checkout_package_dir.mkdir(parents=True)
            (checkout_root / ".git").mkdir()
            (checkout_package_dir / "agents.yaml").write_text("agents:\n", encoding="utf-8")
            (project_root / ".arms").mkdir()
            (project_root / ".arms" / "SESSION.md").write_text(
                """# ARMS Session Log
Generated: old

## Environment
- ARMS Root: /tmp/fake
- Engine Version: 1.5.2+dirty
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

## Completed Tasks
- None

## Blockers
None
""".format(root=project_root),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with mock.patch.object(session_module, "__version__", "1.5.0"), mock.patch.object(
                session_module,
                "resolve_version",
                return_value="1.5.2+dirty",
            ), mock.patch.object(
                sys,
                "argv",
                ["arms", "init", "--root", str(checkout_root)],
            ), redirect_stdout(stdout):
                with self.assertRaises(SystemExit):
                    init_arms.enforce_engine_version_guard(str(project_root), str(checkout_package_dir))

            output = stdout.getvalue()
            self.assertIn("A newer local engine checkout is available:", output)
            self.assertIn(str(checkout_root), output)
            self.assertIn("PYTHONPATH=", output)
            self.assertIn("-m arms_engine.init_arms init --root", output)

    def test_run_init_once_existing_project_generates_inferred_brand_and_prompts(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "pyproject.toml").write_text(
                """[project]
name = "orbitops"
description = "Automate operational approvals and audit workflows."
""",
                encoding="utf-8",
            )

            result = init_arms.run_init_once(
                str(project_root),
                str(ARMS_ROOT),
                "init yolo",
                True,
                show_banner=False,
            )

            brand = (project_root / ".arms" / "BRAND.md").read_text(encoding="utf-8")
            synthesis = (project_root / ".arms" / "CONTEXT_SYNTHESIS.md").read_text(encoding="utf-8")
            prompts = (project_root / ".arms" / "GENERATED_PROMPTS.md").read_text(encoding="utf-8")

            self.assertEqual(result["status"], "complete")
            self.assertIn("- **Project Name:** orbitops", brand)
            self.assertIn("Automate operational approvals and audit workflows.", brand)
            self.assertIn("## Project Overview", synthesis)
            self.assertIn("## Master Build Prompt", prompts)

    def test_run_init_once_normalizes_repo_root_override_to_package_root(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "pyproject.toml").write_text(
                """[project]
name = "orbitops"
description = "Automate operational approvals and audit workflows."
""",
                encoding="utf-8",
            )

            result = init_arms.run_init_once(
                str(project_root),
                str(REPO_ROOT),
                "init yolo",
                True,
                show_banner=False,
            )

            self.assertEqual(result["status"], "complete")
            session = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            self.assertIn(f"- ARMS Root: {ARMS_ROOT}", session)

    def test_run_init_once_raises_context_mismatch_until_overwrite_is_confirmed(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".arms").mkdir()
            (project_root / ".gemini").mkdir()
            (project_root / ".arms" / "BRAND.md").write_text(
                """# Brand Context
- **Project Name:** Demo
- **Mission:** Ship useful software.
- **Vision:** Keep teams aligned.
- **Personality:** Technical
- **Voice & Tone:** Clear
- **Primary Audience:** Developers
- **Core Values:** Reliability
- **Differentiation:** Faster orchestration
- **Color Palette:** Slate
- **Typography:** Inter
- **Logo Status:** Pending
- **Visual Direction:** Dark
- **Project Type:** Web Application
- **Design Priority:** Product clarity
- **Preferred Tech Stack:** Next.js + Supabase + shadcn/ui (latest stable)
- **Deployment Target:** Vercel
- **Backend / Data Layer:** Supabase
- **Authentication Requirement:** OAuth
- **Technical Constraints:** TypeScript only
- **Experience Type:** Marketing site
- **Industry / Business Niche:** SaaS
- **Service Area / Local SEO Target:** Worldwide
- **Required Website Sections:** Header/Nav, Hero, Features, CTA, Footer
- **Primary Calls to Action:** Start Free
- **Icon System:** Lucide
- **Image Requirements:** 5+ images
- **SEO Focus:** Workflow automation
""",
                encoding="utf-8",
            )
            (project_root / ".arms" / "SESSION.md").write_text(
                """# ARMS Session Log
Generated: old

## Environment
- ARMS Root: /tmp/fake
- Engine Version: 1.0.0
- Project Root: /tmp/other-project
- Project Name: Other
- Execution Mode: Parallel
- YOLO Mode: Disabled

## Active Agents
- arms-main-agent

## Active Skills
- arms-orchestrator [Active]

## Active Tasks
| # | Task | Assigned Agent | Active Skill | Dependencies | Status |
|---|------|----------------|--------------|--------------|--------|

## Completed Tasks
- None

## Blockers
None
""",
                encoding="utf-8",
            )

            with self.assertRaises(init_arms.SessionContextMismatchError):
                init_arms.run_init_once(
                    str(project_root),
                    str(ARMS_ROOT),
                    "init",
                    False,
                    show_banner=False,
                )

            result = init_arms.run_init_once(
                str(project_root),
                str(ARMS_ROOT),
                "init",
                False,
                show_banner=False,
                context_overwrite=True,
            )

            self.assertEqual(result["status"], "complete")
            session_content = (project_root / ".arms" / "SESSION.md").read_text(encoding="utf-8")
            self.assertIn(f"- Project Root: {project_root}", session_content)

    def test_run_init_once_warns_when_version_resolution_falls_back(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            stdout = io.StringIO()
            with mock.patch.object(cli_module, "__version__", "0.0.0-dev"), mock.patch.object(
                session_module, "__version__", "0.0.0-dev"
            ), redirect_stdout(stdout):
                init_arms.run_init_once(
                    str(project_root),
                    str(ARMS_ROOT),
                    "init",
                    False,
                    show_banner=True,
                )

            self.assertIn("Could not resolve engine version", stdout.getvalue())

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
