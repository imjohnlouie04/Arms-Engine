"""Tests for arms_engine.cli module — focused on argument parsing and routing helpers."""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from arms_engine.cli import (
    get_arms_root,
    has_project_root_markers,
    normalize_arms_root,
)


class TestGetArmsRoot(unittest.TestCase):
    def test_returns_absolute_path_to_package_directory(self):
        root = get_arms_root()
        self.assertTrue(os.path.isabs(root))
        self.assertTrue(os.path.isdir(root))

    def test_contains_agents_yaml(self):
        root = get_arms_root()
        self.assertTrue(os.path.exists(os.path.join(root, "agents.yaml")))


class TestNormalizeArmsRoot(unittest.TestCase):
    def test_resolves_parent_dir_containing_arms_engine_package(self):
        arms_root = get_arms_root()
        parent = os.path.dirname(arms_root)
        result = normalize_arms_root(parent)
        self.assertEqual(result, arms_root)

    def test_returns_absolute_path_for_arms_engine_itself(self):
        arms_root = get_arms_root()
        result = normalize_arms_root(arms_root)
        self.assertTrue(os.path.isabs(result))

    def test_returns_path_unchanged_for_arbitrary_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = normalize_arms_root(tmpdir)
            self.assertEqual(result, os.path.abspath(tmpdir))


class TestHasProjectRootMarkers(unittest.TestCase):
    def test_detects_git_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".git"))
            self.assertTrue(has_project_root_markers(tmpdir))

    def test_detects_arms_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".arms"))
            self.assertTrue(has_project_root_markers(tmpdir))

    def test_detects_package_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "package.json"), "w").close()
            self.assertTrue(has_project_root_markers(tmpdir))

    def test_detects_legacy_brand_md(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "BRAND.md"), "w").close()
            self.assertTrue(has_project_root_markers(tmpdir))

    def test_detects_two_hint_markers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "MEMORY.md"), "w").close()
            open(os.path.join(tmpdir, "RULES.md"), "w").close()
            self.assertTrue(has_project_root_markers(tmpdir))

    def test_single_hint_marker_not_enough(self):
        # Note: on case-insensitive filesystems (macOS), MEMORY.md and memory.md
        # are the same file, so this test uses a marker name with no lower-case twin.
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "agents.yaml"), "w").close()
            self.assertFalse(has_project_root_markers(tmpdir))

    def test_empty_directory_is_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertFalse(has_project_root_markers(tmpdir))


class TestCliArgValidation(unittest.TestCase):
    """Exercises the early argument validation added to main()."""

    def _run_main(self, argv):
        """Run arms main() with the given argv, capturing SystemExit."""
        with patch.object(sys, "argv", ["arms"] + argv):
            from arms_engine.cli import main
            try:
                main()
                return 0
            except SystemExit as exc:
                return exc.code

    def test_invalid_task_id_exits_nonzero(self):
        code = self._run_main(["task", "update", "--task-id", "not-a-number"])
        self.assertNotEqual(code, 0)

    def test_valid_task_id_does_not_fail_early(self):
        # Providing a valid task-id should not trigger the early validation exit.
        # (It may fail for other reasons, but not exit code 1 from arg validation.)
        # We only check that the error message path is NOT triggered.
        import io
        from contextlib import redirect_stdout
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(sys, "argv", ["arms", "task", "done", "--task-id", "3"]):
                with patch("arms_engine.cli.get_project_root", return_value=tmpdir):
                    with redirect_stdout(output):
                        try:
                            from arms_engine.cli import main
                            main()
                        except SystemExit:
                            pass
        self.assertNotIn("must be a positive integer", output.getvalue())

    def test_empty_section_exits_nonzero(self):
        code = self._run_main(["memory", "draft", "--section", "  ", "--lesson", "some lesson"])
        self.assertNotEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
