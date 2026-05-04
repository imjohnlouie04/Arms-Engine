import unittest

from arms_engine.release import (
    build_next_step,
    format_count_label,
    identify_release_validation_command,
    recommend_next_command,
    summarize_category_status,
    summarize_release_gate,
)


class IdentifyReleaseCommandTests(unittest.TestCase):
    def test_recognises_release_check(self):
        self.assertTrue(identify_release_validation_command(("release", "check")))

    def test_case_insensitive(self):
        self.assertTrue(identify_release_validation_command(("Release", "Check")))

    def test_rejects_unknown_command(self):
        self.assertFalse(identify_release_validation_command(("release", "deploy")))

    def test_rejects_partial_command(self):
        self.assertFalse(identify_release_validation_command(("release",)))

    def test_ignores_extra_whitespace(self):
        self.assertTrue(identify_release_validation_command(("  release  ", "  check  ")))


class SummarizeReleaseGateTests(unittest.TestCase):
    def test_blocked_when_fail(self):
        self.assertEqual(summarize_release_gate({"fail": 1, "warn": 0, "ok": 5}), "BLOCKED")

    def test_ready_with_warnings_when_warn_only(self):
        self.assertEqual(summarize_release_gate({"fail": 0, "warn": 2, "ok": 3}), "READY WITH WARNINGS")

    def test_ready_when_no_issues(self):
        self.assertEqual(summarize_release_gate({"fail": 0, "warn": 0, "ok": 8}), "READY")


class SummarizeCategoryStatusTests(unittest.TestCase):
    def test_fail_dominates(self):
        checks = [{"status": "ok"}, {"status": "fail"}, {"status": "warn"}]
        self.assertEqual(summarize_category_status(checks), "fail")

    def test_warn_when_no_fail(self):
        checks = [{"status": "ok"}, {"status": "warn"}]
        self.assertEqual(summarize_category_status(checks), "warn")

    def test_ok_when_all_ok(self):
        checks = [{"status": "ok"}, {"status": "ok"}]
        self.assertEqual(summarize_category_status(checks), "ok")

    def test_empty_list_is_ok(self):
        self.assertEqual(summarize_category_status([]), "ok")


class FormatCountLabelTests(unittest.TestCase):
    def test_empty_string_for_zero(self):
        self.assertEqual(format_count_label(0), "")

    def test_parenthetical_for_nonzero(self):
        self.assertEqual(format_count_label(3), " (3)")


class RecommendNextCommandTests(unittest.TestCase):
    def test_recommends_doctor_on_workspace_health_fail(self):
        result = recommend_next_command({"fail": 1}, ["Workspace Health"])
        self.assertIn("arms doctor", result)

    def test_recommends_fix_on_generic_fail(self):
        result = recommend_next_command({"fail": 1}, ["Protocol Readiness"])
        self.assertIn("blocking release issues", result)

    def test_recommends_run_deploy_on_warnings_only(self):
        result = recommend_next_command({"fail": 0, "warn": 2}, [])
        self.assertIn("arms run deploy", result)

    def test_recommends_run_deploy_on_all_clear(self):
        result = recommend_next_command({"fail": 0, "warn": 0}, [])
        self.assertIn("arms run deploy", result)


class BuildNextStepTests(unittest.TestCase):
    def test_halt_on_fail(self):
        result = build_next_step({"fail": 2, "warn": 0})
        self.assertIn("HALT", result)
        self.assertIn("blocking issues", result)

    def test_continue_on_warn(self):
        result = build_next_step({"fail": 0, "warn": 1})
        self.assertIn("HALT", result)
        self.assertIn("warnings", result)

    def test_proceed_on_ok(self):
        result = build_next_step({"fail": 0, "warn": 0})
        self.assertIn("HALT", result)
        self.assertIn("passed", result)


if __name__ == "__main__":
    unittest.main()
