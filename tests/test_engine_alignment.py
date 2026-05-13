import unittest
from pathlib import Path

from arms_engine.metadata import (
    REPORT_HISTORY_FILENAME,
    SESSION_BOOTSTRAP_HEADINGS,
    TASK_TABLE_COLUMNS,
    latest_report_filename,
)
from arms_engine.session import read_text_file
from arms_engine.skills import build_agent_sync_content, load_agents_registry
from arms_engine.update_docs import get_agent_docs


REPO_ROOT = Path(__file__).resolve().parents[1]
ARMS_ROOT = REPO_ROOT / "arms_engine"


def extract_heading_section(content, heading):
    lines = content.splitlines()
    heading_level = len(heading) - len(heading.lstrip("#"))
    captured = []
    active = False
    for line in lines:
        stripped = line.strip()
        if not active:
            if stripped == heading:
                active = True
                captured.append(stripped)
            continue
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if level <= heading_level:
                break
        captured.append(line.rstrip())
    return "\n".join(captured).strip()


class EngineAlignmentTests(unittest.TestCase):
    def test_readme_agent_roster_matches_agents_yaml(self):
        readme_content = read_text_file(str(REPO_ROOT / "README.md"))
        start_marker = "<!-- AGENT_ROSTER_START -->"
        end_marker = "<!-- AGENT_ROSTER_END -->"
        start_index = readme_content.rfind(start_marker)
        end_index = readme_content.rfind(end_marker)
        self.assertNotEqual(start_index, -1)
        self.assertNotEqual(end_index, -1)
        self.assertGreater(end_index, start_index)
        actual_roster = readme_content[start_index + len(start_marker):end_index].strip()
        self.assertEqual(actual_roster, get_agent_docs(str(ARMS_ROOT)).strip())

    def test_tracked_mirrors_match_engine_sources(self):
        self.assertEqual(
            read_text_file(str(ARMS_ROOT / "ENGINE.md")),
            read_text_file(str(REPO_ROOT / ".arms" / "ENGINE.md")),
        )
        self.assertEqual(
            read_text_file(str(ARMS_ROOT / "AGENTS.md")),
            read_text_file(str(REPO_ROOT / "AGENTS.md")),
        )
        self.assertEqual(
            read_text_file(str(ARMS_ROOT / "skills" / "arms-orchestrator" / "SKILL.md")),
            read_text_file(str(REPO_ROOT / ".github" / "skills" / "arms-orchestrator" / "SKILL.md")),
        )
        self.assertEqual(
            read_text_file(str(ARMS_ROOT / "skills" / "arms-orchestrator" / "SKILL.md")),
            read_text_file(str(REPO_ROOT / ".arms" / "skills" / "arms-orchestrator" / "SKILL.md")),
        )

        registry = {
            agent["name"]: agent
            for agent in load_agents_registry(str(ARMS_ROOT))
        }
        expected_agent = build_agent_sync_content(
            read_text_file(str(ARMS_ROOT / "agents" / "arms-main-agent.md")),
            registry.get("arms-main-agent", {}),
        )
        self.assertEqual(
            expected_agent,
            read_text_file(str(REPO_ROOT / ".github" / "agents" / "arms-main-agent.md")),
        )
        self.assertEqual(
            expected_agent,
            read_text_file(str(REPO_ROOT / ".gemini" / "agents" / "arms-main-agent.md")),
        )

        expected_frontend_agent = build_agent_sync_content(
            read_text_file(str(ARMS_ROOT / "agents" / "arms-frontend-agent.md")),
            registry.get("arms-frontend-agent", {}),
        )
        self.assertEqual(
            expected_frontend_agent,
            read_text_file(str(REPO_ROOT / ".github" / "agents" / "arms-frontend-agent.md")),
        )
        self.assertEqual(
            expected_frontend_agent,
            read_text_file(str(REPO_ROOT / ".gemini" / "agents" / "arms-frontend-agent.md")),
        )

    def test_project_owned_instruction_intake_sections_match(self):
        heading = "### ARMS Orchestration & Intake"
        gemini_section = extract_heading_section(read_text_file(str(REPO_ROOT / "GEMINI.md")), heading)
        gemini_cli_section = extract_heading_section(
            read_text_file(str(REPO_ROOT / ".gemini" / "GEMINI.md")),
            heading,
        )
        copilot_section = extract_heading_section(
            read_text_file(str(REPO_ROOT / ".github" / "copilot-instructions.md")),
            heading,
        )
        self.assertTrue(gemini_section)
        self.assertEqual(gemini_section, gemini_cli_section)
        self.assertEqual(gemini_section, copilot_section)

    def test_protocol_docs_match_canonical_report_metadata(self):
        readme_content = read_text_file(str(REPO_ROOT / "README.md"))
        self.assertIn("./.arms/reports/{}".format(latest_report_filename("review")), readme_content)
        self.assertIn("./.arms/reports/{}".format(latest_report_filename("release-notes")), readme_content)
        self.assertIn("./.arms/reports/{}".format(REPORT_HISTORY_FILENAME), readme_content)

        review_protocol = read_text_file(str(ARMS_ROOT / "workflow" / "REVIEW_PROTOCOL.md"))
        self.assertIn("./.arms/reports/{}".format(latest_report_filename("review")), review_protocol)
        self.assertIn("./.arms/reports/{}".format(REPORT_HISTORY_FILENAME), review_protocol)

        deploy_protocol = read_text_file(str(ARMS_ROOT / "workflow" / "DEPLOY_PROTOCOL.md"))
        self.assertIn("./.arms/reports/{}".format(latest_report_filename("release-notes")), deploy_protocol)
        self.assertIn("./.arms/reports/{}".format(REPORT_HISTORY_FILENAME), deploy_protocol)

        fix_protocol = read_text_file(str(ARMS_ROOT / "workflow" / "FIX_ISSUE_PROTOCOL.md"))
        self.assertIn("./.arms/reports/{}".format(latest_report_filename("review")), fix_protocol)
        self.assertIn(TASK_TABLE_COLUMNS, fix_protocol)

    def test_orchestrator_skill_template_matches_canonical_session_headings(self):
        skill_content = read_text_file(str(ARMS_ROOT / "skills" / "arms-orchestrator" / "SKILL.md"))
        start_marker = "### SESSION.md Bootstrap Template"
        end_marker = "### MEMORY.md Bootstrap Template"
        start_index = skill_content.find(start_marker)
        end_index = skill_content.find(end_marker, start_index)
        bootstrap_section = skill_content[start_index:end_index]

        self.assertTrue(bootstrap_section)
        last_index = -1
        for heading in SESSION_BOOTSTRAP_HEADINGS:
            marker = "## {}".format(heading)
            index = bootstrap_section.find(marker)
            self.assertNotEqual(index, -1, msg="Missing {!r} in SESSION.md bootstrap template".format(marker))
            self.assertGreater(index, last_index, msg="Out-of-order {!r} in SESSION.md bootstrap template".format(marker))
            last_index = index

    def test_orchestrator_skill_reference_inventory_lists_brand_and_scope(self):
        skill_content = read_text_file(str(ARMS_ROOT / "skills" / "arms-orchestrator" / "SKILL.md"))
        references_section = extract_heading_section(skill_content, "## Reference Files")

        self.assertTrue(references_section)
        self.assertIn("`brand-and-scope.md`", references_section)

    def test_frontend_mobile_mandate_is_scoped_to_mobile_layouts(self):
        frontend_agent = read_text_file(str(ARMS_ROOT / "agents" / "arms-frontend-agent.md"))
        frontend_rules = read_text_file(str(ARMS_ROOT / "agents.yaml"))

        self.assertIn("On mobile and Mobile Extended layouts", frontend_agent)
        self.assertIn("do not apply that sizing mandate to desktop-only layouts", frontend_agent)
        self.assertIn("while preserving normal desktop density", frontend_rules)


if __name__ == "__main__":
    unittest.main()
