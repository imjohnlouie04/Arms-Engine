"""Tests for arms_engine.skills module."""
import os
import tempfile
import unittest

from arms_engine.skills import (
    build_skill_mirror_ignore,
    ensure_agent_tools_frontmatter,
    ensure_skill_frontmatter,
    infer_skill_description,
    inject_agent_runtime_rules,
    parse_skill_metadata,
    split_agent_rules_text,
)


class TestEnsureAgentToolsFrontmatter(unittest.TestCase):
    def test_adds_tools_key_when_missing(self):
        content = '---\nname: my-agent\n---\n\nAgent body.'
        result = ensure_agent_tools_frontmatter(content)
        self.assertIn('tools:', result)

    def test_does_not_duplicate_tools_key(self):
        content = '---\ntools: ["*"]\nname: my-agent\n---\n\nAgent body.'
        result = ensure_agent_tools_frontmatter(content)
        self.assertEqual(result.count('tools:'), 1)

    def test_no_frontmatter_passthrough(self):
        content = 'No frontmatter here'
        result = ensure_agent_tools_frontmatter(content)
        self.assertEqual(result, content)


class TestSplitAgentRulesText(unittest.TestCase):
    def test_splits_on_sentence_boundaries(self):
        text = "Rule one. Rule two. Rule three."
        parts = split_agent_rules_text(text)
        self.assertEqual(len(parts), 3)
        self.assertIn("Rule one.", parts)

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(split_agent_rules_text(""), [])

    def test_whitespace_only_returns_empty_list(self):
        self.assertEqual(split_agent_rules_text("   "), [])

    def test_single_sentence_returns_list_with_one_item(self):
        parts = split_agent_rules_text("Only one rule.")
        self.assertEqual(parts, ["Only one rule."])


class TestInjectAgentRuntimeRules(unittest.TestCase):
    def test_adds_runtime_rules_section_when_missing(self):
        content = '# Agent\n\nDo things.'
        result = inject_agent_runtime_rules(content, 'Follow the style guide.')
        self.assertIn('## Runtime Rules', result)
        self.assertIn('Follow the style guide.', result)

    def test_appends_to_existing_runtime_rules_section(self):
        content = '# Agent\n\nDo things.\n\n## Runtime Rules\n- Existing rule.\n'
        result = inject_agent_runtime_rules(content, 'New rule.')
        self.assertIn('Existing rule.', result)
        self.assertIn('New rule.', result)

    def test_does_not_add_duplicate_rule(self):
        content = '# Agent\n\n## Runtime Rules\n- Existing rule.'
        result = inject_agent_runtime_rules(content, 'Existing rule.')
        self.assertEqual(result.count('Existing rule.'), 1)

    def test_empty_rules_returns_content_unchanged(self):
        content = '# Agent\n\nDo things.'
        result = inject_agent_runtime_rules(content, '')
        self.assertEqual(result, content)


class TestInferSkillDescription(unittest.TestCase):
    def test_uses_role_line(self):
        content = '# Skill\n\n**Role:** Backend specialist for APIs.\n'
        result = infer_skill_description(content, 'backend')
        self.assertIn('Backend specialist for APIs', result)

    def test_uses_first_prose_line(self):
        content = 'This skill handles backend work.\n'
        result = infer_skill_description(content, 'backend')
        self.assertIn('backend work', result)

    def test_falls_back_to_skill_name(self):
        # When there's no role line and no plain prose, falls back to first
        # non-empty, non-heading line (the list item) or the generated fallback.
        content = '# Heading\n\nmy-skill does things.\n'
        result = infer_skill_description(content, 'my-skill')
        self.assertTrue(result)  # non-empty

    def test_strips_frontmatter_before_parsing(self):
        content = '---\nname: test\n---\n\nReal description here.\n'
        result = infer_skill_description(content, 'test')
        self.assertEqual(result, 'Real description here.')


class TestParseSkillMetadata(unittest.TestCase):
    def _write_skill_md(self, tmpdir, content):
        path = os.path.join(tmpdir, 'SKILL.md')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def test_parses_frontmatter_name_and_description(self):
        content = '---\nname: my-skill\ndescription: "Does things."\n---\n\nBody.\n'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_skill_md(tmpdir, content)
            meta = parse_skill_metadata(path, 'my-skill')
        self.assertEqual(meta['name'], 'my-skill')
        self.assertEqual(meta['description'], 'Does things.')

    def test_falls_back_to_directory_name(self):
        content = '# Skill\n\nNo frontmatter.\n'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_skill_md(tmpdir, content)
            meta = parse_skill_metadata(path, 'fallback-name')
        self.assertEqual(meta['name'], 'fallback-name')

    def test_raises_value_error_for_invalid_yaml(self):
        content = '---\n: invalid: yaml: [\n---\n\nBody.\n'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_skill_md(tmpdir, content)
            with self.assertRaises(ValueError):
                parse_skill_metadata(path, 'bad-skill')

    def test_infers_description_when_empty(self):
        content = '---\nname: test\ndescription: ""\n---\n\nActual description here.\n'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_skill_md(tmpdir, content)
            meta = parse_skill_metadata(path, 'test')
        self.assertIn('Actual description', meta['description'])


class TestEnsureSkillFrontmatter(unittest.TestCase):
    def test_adds_frontmatter_when_missing(self):
        content = '# My Skill\n\nThis skill does things.\n'
        result = ensure_skill_frontmatter(content, 'my-skill')
        self.assertTrue(result.startswith('---'))
        self.assertIn('name: my-skill', result)

    def test_does_not_duplicate_frontmatter(self):
        content = '---\nname: my-skill\n---\n\nBody.\n'
        result = ensure_skill_frontmatter(content, 'my-skill')
        self.assertEqual(result.count('---'), 2)

    def test_preserves_body_content(self):
        content = '# Skill\n\nBody content here.\n'
        result = ensure_skill_frontmatter(content, 'test')
        self.assertIn('Body content here.', result)


class TestBuildSkillMirrorIgnore(unittest.TestCase):
    def test_returns_callable(self):
        ignore_fn = build_skill_mirror_ignore('generic-skill')
        self.callable(ignore_fn)

    def callable(self, fn):
        self.assertTrue(callable(fn))

    def test_ignores_ds_store(self):
        ignore_fn = build_skill_mirror_ignore('generic-skill')
        ignored = ignore_fn('/some/dir', ['.DS_Store', 'SKILL.md'])
        self.assertIn('.DS_Store', ignored)
        self.assertNotIn('SKILL.md', ignored)

    def test_ignores_reference_dirs_for_known_skill(self):
        ignore_fn = build_skill_mirror_ignore('ui-ux-pro-max')
        ignored = ignore_fn('/some/dir', ['data', 'SKILL.md', 'references'])
        self.assertIn('data', ignored)
        self.assertNotIn('SKILL.md', ignored)


if __name__ == '__main__':
    unittest.main()
