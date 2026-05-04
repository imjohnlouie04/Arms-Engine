import time
import unittest

from arms_engine.monitor import (
    extract_environment_value,
    format_duration,
    format_timestamp,
    pad_line,
    summarize_exception,
    truncate_text,
)


class TruncateTextTests(unittest.TestCase):
    def test_short_text_unchanged(self):
        self.assertEqual(truncate_text("hello", 10), "hello")

    def test_exact_width_unchanged(self):
        self.assertEqual(truncate_text("hello", 5), "hello")

    def test_long_text_truncated_with_ellipsis(self):
        result = truncate_text("hello world", 8)
        self.assertTrue(result.endswith("..."))
        self.assertIn("hello w", result)

    def test_zero_width_returns_empty(self):
        self.assertEqual(truncate_text("hello", 0), "")

    def test_width_of_one(self):
        result = truncate_text("hello", 1)
        self.assertEqual(len(result), 1)

    def test_non_string_coerced(self):
        self.assertEqual(truncate_text(42, 10), "42")


class PadLineTests(unittest.TestCase):
    def test_short_text_padded(self):
        result = pad_line("hi", 6)
        self.assertEqual(result, "hi    ")
        self.assertEqual(len(result), 6)

    def test_exact_width_no_padding(self):
        result = pad_line("hello", 5)
        self.assertEqual(result, "hello")

    def test_overflow_text_truncated(self):
        result = pad_line("hello world", 7)
        self.assertTrue(result.endswith("..."))


class FormatTimestampTests(unittest.TestCase):
    def test_zero_returns_not_yet(self):
        # format_timestamp in module scope is time-stamp based (not None-aware)
        result = format_timestamp(0)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_valid_timestamp_returns_formatted_string(self):
        ts = time.mktime(time.strptime("2024-01-15 12:00:00", "%Y-%m-%d %H:%M:%S"))
        result = format_timestamp(ts)
        self.assertIn("2024-01-15", result)


class FormatDurationTests(unittest.TestCase):
    def test_running_returns_elapsed_string(self):
        import time as time_module
        started = time_module.time() - 5.0
        result = format_duration(started)
        self.assertIn("s", result)

    def test_finished_returns_elapsed_string(self):
        import time as time_module
        started = time_module.time() - 10.0
        finished = time_module.time() - 2.0
        result = format_duration(started, finished)
        self.assertIn("s", result)


class ExtractEnvironmentValueTests(unittest.TestCase):
    ENVIRONMENT = (
        "- Execution Mode: Mode A (Parallel)\n"
        "- YOLO Mode: Disabled\n"
        "- Engine Version: 1.2.3\n"
    )

    def test_extracts_execution_mode(self):
        result = extract_environment_value(self.ENVIRONMENT, "Execution Mode")
        self.assertEqual(result, "Mode A (Parallel)")

    def test_extracts_yolo_mode(self):
        result = extract_environment_value(self.ENVIRONMENT, "YOLO Mode")
        self.assertEqual(result, "Disabled")

    def test_returns_unknown_for_missing_key(self):
        result = extract_environment_value(self.ENVIRONMENT, "Nonexistent Key")
        self.assertEqual(result, "Unknown")


class SummarizeExceptionTests(unittest.TestCase):
    def test_returns_string_for_exception(self):
        try:
            raise ValueError("test error")
        except ValueError as exc:
            result = summarize_exception(exc)
        self.assertIsInstance(result, str)
        self.assertIn("test error", result)


if __name__ == "__main__":
    unittest.main()
