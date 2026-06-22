"""Tests for arms_engine.model_routing and the model-tier sync helpers in arms_engine.skills."""
import os
import tempfile
import unittest

from arms_engine.model_routing import (
    DEFAULT_MODEL_TIER,
    MODEL_TIERS,
    load_model_routing,
    normalize_model_tier,
    resolve_agent_model,
)
from arms_engine.skills import (
    ensure_agent_model_frontmatter,
    parse_agent_frontmatter_and_body,
    render_codex_agent_toml,
    sync_agents_codex,
)


SAMPLE_ROUTING = {
    "platforms": {
        "claude": {
            "economy": "haiku",
            "standard": "sonnet",
            "power": "opus",
        },
        "codex": {
            "economy": {"model": "gpt-5.4-mini", "model_reasoning_effort": "low"},
            "standard": {"model": "gpt-5.4", "model_reasoning_effort": "medium"},
            "power": {"model": "gpt-5.5", "model_reasoning_effort": "high"},
        },
        "gemini": {
            "economy": "gemini-flash-latest",
            "standard": "gemini-flash-latest",
            "power": "gemini-pro-latest",
        },
    }
}


class TestNormalizeModelTier(unittest.TestCase):
    def test_recognised_tiers_pass_through(self):
        for tier in MODEL_TIERS:
            self.assertEqual(normalize_model_tier(tier), tier)

    def test_unknown_value_falls_back_to_default(self):
        self.assertEqual(normalize_model_tier("ultra"), DEFAULT_MODEL_TIER)

    def test_none_falls_back_to_default(self):
        self.assertEqual(normalize_model_tier(None), DEFAULT_MODEL_TIER)

    def test_is_case_and_whitespace_insensitive(self):
        self.assertEqual(normalize_model_tier(" Power \n"), "power")


class TestLoadModelRouting(unittest.TestCase):
    def test_returns_empty_dict_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(load_model_routing(tmpdir), {})

    def test_parses_valid_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "model_routing.yaml")
            with open(path, "w", encoding="utf-8") as f:
                f.write("platforms:\n  claude:\n    standard: sonnet\n")
            routing = load_model_routing(tmpdir)
        self.assertEqual(routing["platforms"]["claude"]["standard"], "sonnet")

    def test_raises_value_error_for_invalid_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "model_routing.yaml")
            with open(path, "w", encoding="utf-8") as f:
                f.write(": invalid: yaml: [\n")
            with self.assertRaises(ValueError):
                load_model_routing(tmpdir)

    def test_raises_value_error_for_non_mapping_top_level(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "model_routing.yaml")
            with open(path, "w", encoding="utf-8") as f:
                f.write("- just\n- a\n- list\n")
            with self.assertRaises(ValueError):
                load_model_routing(tmpdir)


class TestResolveAgentModel(unittest.TestCase):
    def test_resolves_claude_model_string(self):
        agent_info = {"model_tier": "power"}
        self.assertEqual(resolve_agent_model(agent_info, "claude", SAMPLE_ROUTING), "opus")

    def test_resolves_gemini_model_string(self):
        agent_info = {"model_tier": "economy"}
        self.assertEqual(resolve_agent_model(agent_info, "gemini", SAMPLE_ROUTING), "gemini-flash-latest")

    def test_resolves_codex_model_dict(self):
        agent_info = {"model_tier": "standard"}
        result = resolve_agent_model(agent_info, "codex", SAMPLE_ROUTING)
        self.assertEqual(result, {"model": "gpt-5.4", "model_reasoning_effort": "medium"})

    def test_missing_model_tier_uses_default(self):
        agent_info = {}
        self.assertEqual(
            resolve_agent_model(agent_info, "claude", SAMPLE_ROUTING),
            SAMPLE_ROUTING["platforms"]["claude"][DEFAULT_MODEL_TIER],
        )

    def test_unconfigured_platform_returns_none(self):
        agent_info = {"model_tier": "standard"}
        self.assertIsNone(resolve_agent_model(agent_info, "copilot", SAMPLE_ROUTING))

    def test_empty_routing_returns_none(self):
        agent_info = {"model_tier": "power"}
        self.assertIsNone(resolve_agent_model(agent_info, "claude", {}))


class TestEnsureAgentModelFrontmatter(unittest.TestCase):
    def test_adds_model_key_when_absent(self):
        content = "---\nname: my-agent\ndescription: Does things.\n---\n\nBody.\n"
        result = ensure_agent_model_frontmatter(content, "opus")
        self.assertIn("model: opus", result)
        self.assertIn("Body.", result)

    def test_replaces_existing_model_key(self):
        content = "---\nname: my-agent\nmodel: sonnet\n---\n\nBody.\n"
        result = ensure_agent_model_frontmatter(content, "opus")
        self.assertIn("model: opus", result)
        self.assertNotIn("model: sonnet", result)
        self.assertEqual(result.count("model:"), 1)

    def test_returns_unchanged_when_model_value_falsy(self):
        content = "---\nname: my-agent\n---\n\nBody.\n"
        self.assertEqual(ensure_agent_model_frontmatter(content, None), content)
        self.assertEqual(ensure_agent_model_frontmatter(content, ""), content)

    def test_returns_unchanged_when_no_frontmatter(self):
        content = "# Just a heading\n\nBody.\n"
        self.assertEqual(ensure_agent_model_frontmatter(content, "opus"), content)


class TestParseAgentFrontmatterAndBody(unittest.TestCase):
    def test_parses_frontmatter_and_body(self):
        content = "---\nname: arms-backend-agent\ndescription: Backend specialist.\n---\n\n# Heading\n\nBody text.\n"
        frontmatter, body = parse_agent_frontmatter_and_body(content)
        self.assertEqual(frontmatter["name"], "arms-backend-agent")
        self.assertEqual(frontmatter["description"], "Backend specialist.")
        self.assertEqual(body, "# Heading\n\nBody text.")

    def test_no_frontmatter_returns_empty_dict(self):
        content = "# Just a heading\n\nBody.\n"
        frontmatter, body = parse_agent_frontmatter_and_body(content)
        self.assertEqual(frontmatter, {})
        self.assertEqual(body, "# Just a heading\n\nBody.")


class TestRenderCodexAgentToml(unittest.TestCase):
    def test_renders_name_and_description(self):
        toml_content = render_codex_agent_toml("arms-backend-agent", "Backend specialist.", "Body text.")
        self.assertIn('name = "arms-backend-agent"', toml_content)
        self.assertIn('description = "Backend specialist."', toml_content)
        self.assertNotIn("model =", toml_content)
        self.assertNotIn("model_reasoning_effort =", toml_content)

    def test_renders_model_config_when_provided(self):
        model_config = {"model": "gpt-5.5", "model_reasoning_effort": "high"}
        toml_content = render_codex_agent_toml("arms-data-agent", "Data specialist.", "Body text.", model_config)
        self.assertIn('model = "gpt-5.5"', toml_content)
        self.assertIn('model_reasoning_effort = "high"', toml_content)

    def test_instructions_use_literal_multiline_string(self):
        instructions = '# Heading\n\nUse "quotes" and \\ backslashes freely.\n'
        toml_content = render_codex_agent_toml("arms-qa-agent", "QA specialist.", instructions)
        self.assertIn("developer_instructions = '''", toml_content)
        self.assertIn('Use "quotes" and \\ backslashes freely.', toml_content)

    def test_escapes_literal_triple_quote_in_instructions(self):
        instructions = "Some text with ''' inside it."
        toml_content = render_codex_agent_toml("arms-qa-agent", "QA specialist.", instructions)
        self.assertNotIn("with ''' inside", toml_content)
        self.assertIn("with '' ' inside", toml_content)

    def test_escapes_quotes_in_description(self):
        toml_content = render_codex_agent_toml('agent', 'Has "quotes" in it.', "Body.")
        self.assertIn('description = "Has \\"quotes\\" in it."', toml_content)


class TestSyncAgentsCodex(unittest.TestCase):
    def _write(self, path, content):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_generates_toml_with_model_routing(self):
        with tempfile.TemporaryDirectory() as arms_root, tempfile.TemporaryDirectory() as project_root:
            self._write(
                os.path.join(arms_root, "agents", "arms-backend-agent.md"),
                "---\nname: arms-backend-agent\ndescription: Backend specialist.\n---\n\n# ARMS Backend Agent\n\nBody.\n",
            )
            self._write(
                os.path.join(arms_root, "agents.yaml"),
                "agents:\n  arms-backend-agent:\n    role: Backend Specialist\n    scope: Backend stuff.\n    model_tier: power\n",
            )
            self._write(
                os.path.join(arms_root, "model_routing.yaml"),
                "platforms:\n  codex:\n    power:\n      model: gpt-5.5\n      model_reasoning_effort: high\n",
            )

            sync_agents_codex(arms_root, project_root)

            toml_path = os.path.join(project_root, ".codex", "agents", "arms-backend-agent.toml")
            self.assertTrue(os.path.exists(toml_path))
            with open(toml_path, "r", encoding="utf-8") as f:
                content = f.read()
        self.assertIn('name = "arms-backend-agent"', content)
        self.assertIn('description = "Backend specialist."', content)
        self.assertIn('model = "gpt-5.5"', content)
        self.assertIn('model_reasoning_effort = "high"', content)
        self.assertIn("# ARMS Backend Agent", content)

    def test_removes_stale_toml_files(self):
        with tempfile.TemporaryDirectory() as arms_root, tempfile.TemporaryDirectory() as project_root:
            self._write(
                os.path.join(arms_root, "agents", "arms-backend-agent.md"),
                "---\nname: arms-backend-agent\ndescription: Backend specialist.\n---\n\nBody.\n",
            )
            self._write(os.path.join(arms_root, "agents.yaml"), "agents:\n  arms-backend-agent:\n    role: Backend\n")
            stale_path = os.path.join(project_root, ".codex", "agents", "arms-removed-agent.toml")
            self._write(stale_path, 'name = "arms-removed-agent"\n')

            sync_agents_codex(arms_root, project_root)

            self.assertFalse(os.path.exists(stale_path))
            self.assertTrue(os.path.exists(os.path.join(project_root, ".codex", "agents", "arms-backend-agent.toml")))


if __name__ == "__main__":
    unittest.main()
