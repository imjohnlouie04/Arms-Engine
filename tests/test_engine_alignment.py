import unittest
from pathlib import Path

from arms_engine.session import read_text_file
from arms_engine.skills import build_agent_sync_content, load_agents_registry
from arms_engine.update_docs import get_agent_docs


REPO_ROOT = Path(__file__).resolve().parents[1]
ARMS_ROOT = REPO_ROOT / "arms_engine"


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


if __name__ == "__main__":
    unittest.main()
