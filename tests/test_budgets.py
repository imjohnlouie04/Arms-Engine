import os
import unittest

from arms_engine.budgets import (
    ARCHIVE_TOKEN_LIMIT,
    AUTO_COMPACT_AGENT_OUTPUT_FILE_LIMIT,
    AUTO_COMPACT_MEMORY_CHAR_LIMIT,
    AUTO_COMPACT_REPORT_FILE_LIMIT,
    AUTO_COMPACT_SESSION_CHAR_LIMIT,
    CONTEXT_SYNTHESIS_TOKEN_BUDGET,
    DEFAULT_TOKEN_BUDGET_WARN_RATIO,
    GENERATED_PROMPTS_TOKEN_BUDGET,
    SESSION_TOKEN_BUDGET,
    WATCH_POLL_INTERVAL_SECONDS,
    _int_env,
)


class IntEnvTests(unittest.TestCase):
    def test_returns_default_when_env_unset(self):
        os.environ.pop("ARMS_TEST_BUDGET_X", None)
        self.assertEqual(_int_env("ARMS_TEST_BUDGET_X", 42), 42)

    def test_returns_env_value_when_set(self):
        os.environ["ARMS_TEST_BUDGET_X"] = "99"
        try:
            self.assertEqual(_int_env("ARMS_TEST_BUDGET_X", 42), 99)
        finally:
            del os.environ["ARMS_TEST_BUDGET_X"]

    def test_falls_back_on_non_integer_value(self):
        os.environ["ARMS_TEST_BUDGET_X"] = "not_a_number"
        try:
            self.assertEqual(_int_env("ARMS_TEST_BUDGET_X", 42), 42)
        finally:
            del os.environ["ARMS_TEST_BUDGET_X"]

    def test_falls_back_on_empty_string(self):
        os.environ["ARMS_TEST_BUDGET_X"] = ""
        try:
            self.assertEqual(_int_env("ARMS_TEST_BUDGET_X", 7), 7)
        finally:
            del os.environ["ARMS_TEST_BUDGET_X"]

    def test_falls_back_on_float_string(self):
        os.environ["ARMS_TEST_BUDGET_X"] = "3.14"
        try:
            self.assertEqual(_int_env("ARMS_TEST_BUDGET_X", 10), 10)
        finally:
            del os.environ["ARMS_TEST_BUDGET_X"]

    def test_strips_whitespace(self):
        os.environ["ARMS_TEST_BUDGET_X"] = "  50  "
        try:
            self.assertEqual(_int_env("ARMS_TEST_BUDGET_X", 10), 50)
        finally:
            del os.environ["ARMS_TEST_BUDGET_X"]


class BudgetConstantTests(unittest.TestCase):
    def test_session_token_budget_positive(self):
        self.assertGreater(SESSION_TOKEN_BUDGET, 0)

    def test_warn_ratio_is_fraction(self):
        self.assertGreater(DEFAULT_TOKEN_BUDGET_WARN_RATIO, 0.0)
        self.assertLess(DEFAULT_TOKEN_BUDGET_WARN_RATIO, 1.0)

    def test_context_synthesis_budget_positive(self):
        self.assertGreater(CONTEXT_SYNTHESIS_TOKEN_BUDGET, 0)

    def test_generated_prompts_budget_positive(self):
        self.assertGreater(GENERATED_PROMPTS_TOKEN_BUDGET, 0)

    def test_auto_compact_limits_positive(self):
        self.assertGreater(AUTO_COMPACT_SESSION_CHAR_LIMIT, 0)
        self.assertGreater(AUTO_COMPACT_MEMORY_CHAR_LIMIT, 0)

    def test_report_file_limit_positive(self):
        self.assertGreater(AUTO_COMPACT_REPORT_FILE_LIMIT, 0)

    def test_agent_output_file_limit_positive(self):
        self.assertGreater(AUTO_COMPACT_AGENT_OUTPUT_FILE_LIMIT, 0)

    def test_archive_token_limit_positive(self):
        self.assertGreater(ARCHIVE_TOKEN_LIMIT, 0)

    def test_watch_poll_interval_positive(self):
        self.assertGreater(WATCH_POLL_INTERVAL_SECONDS, 0.0)
        self.assertIsInstance(WATCH_POLL_INTERVAL_SECONDS, float)


class BudgetEnvOverrideTests(unittest.TestCase):
    def test_session_budget_overridable(self):
        os.environ["ARMS_SESSION_TOKEN_BUDGET"] = "5000"
        try:
            from importlib import reload
            import arms_engine.budgets as budgets_module
            reload(budgets_module)
            self.assertEqual(budgets_module.SESSION_TOKEN_BUDGET, 5000)
        finally:
            del os.environ["ARMS_SESSION_TOKEN_BUDGET"]
            from importlib import reload
            import arms_engine.budgets as budgets_module
            reload(budgets_module)

    def test_watch_poll_overridable(self):
        os.environ["ARMS_WATCH_POLL_INTERVAL_SECONDS"] = "5.0"
        try:
            from importlib import reload
            import arms_engine.budgets as budgets_module
            reload(budgets_module)
            self.assertAlmostEqual(budgets_module.WATCH_POLL_INTERVAL_SECONDS, 5.0)
        finally:
            del os.environ["ARMS_WATCH_POLL_INTERVAL_SECONDS"]
            from importlib import reload
            import arms_engine.budgets as budgets_module
            reload(budgets_module)


if __name__ == "__main__":
    unittest.main()
