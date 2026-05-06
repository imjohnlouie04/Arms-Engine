"""Tests for task log debounce mechanism to prevent rapid duplicate calls from IDE."""

import json
import os
import tempfile
import time
import unittest

from arms_engine.paths import WorkspacePaths
from arms_engine.tasks import (
    check_task_log_debounce,
    update_task_log_debounce,
)


class TaskLogDebounceTests(unittest.TestCase):
    """Ensure rapid repeated calls to arms task log don't create duplicates."""

    def setUp(self):
        """Create temporary project root for each test."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.project_root = self.tmpdir.name
        # Create .arms directory
        os.makedirs(WorkspacePaths(self.project_root).arms_dir, exist_ok=True)

    def tearDown(self):
        """Clean up temporary directory."""
        self.tmpdir.cleanup()

    def test_no_debounce_when_lock_missing(self):
        """First call should not be debounced (no lock file exists)."""
        result = check_task_log_debounce(self.project_root, "Create a feature")
        self.assertFalse(result)

    def test_debounce_immediate_duplicate(self):
        """Immediate second call with same task should be debounced."""
        task = "Create a feature"
        update_task_log_debounce(self.project_root, task)
        result = check_task_log_debounce(self.project_root, task)
        self.assertTrue(result)

    def test_debounce_case_insensitive(self):
        """Debounce matching is case-insensitive."""
        task_lower = "create a feature"
        task_upper = "CREATE A FEATURE"
        update_task_log_debounce(self.project_root, task_lower)
        result = check_task_log_debounce(self.project_root, task_upper)
        self.assertTrue(result)

    def test_no_debounce_different_task(self):
        """Different task should not be debounced."""
        task1 = "Create a feature"
        task2 = "Different task"
        update_task_log_debounce(self.project_root, task1)
        result = check_task_log_debounce(self.project_root, task2)
        self.assertFalse(result)

    def test_debounce_timeout(self):
        """Debounce should expire after timeout period."""
        task = "Create a feature"
        update_task_log_debounce(self.project_root, task)
        
        result_immediate = check_task_log_debounce(self.project_root, task, debounce_seconds=1)
        self.assertTrue(result_immediate)
        
        time.sleep(1.1)
        result_after = check_task_log_debounce(self.project_root, task, debounce_seconds=1)
        self.assertFalse(result_after)

    def test_debounce_lock_file_structure(self):
        """Lock file should contain task and timestamp."""
        task = "Create a feature"
        update_task_log_debounce(self.project_root, task)
        
        lock_path = WorkspacePaths(self.project_root).task_log_lock
        self.assertTrue(os.path.exists(lock_path))
        
        with open(lock_path, "r") as f:
            lock_data = json.load(f)
        
        self.assertEqual(lock_data["task"], task)
        self.assertIn("timestamp", lock_data)
        self.assertIsInstance(lock_data["timestamp"], (int, float))

    def test_debounce_malformed_lock_file(self):
        """Malformed lock file should not crash debounce check."""
        lock_path = WorkspacePaths(self.project_root).task_log_lock
        with open(lock_path, "w") as f:
            f.write("invalid json {")
        
        result = check_task_log_debounce(self.project_root, "Task")
        self.assertFalse(result)

    def test_concurrent_task_debounce(self):
        """Rapid calls with different tasks should all be allowed."""
        task1 = "Task 1"
        task2 = "Task 2"
        task3 = "Task 3"
        
        result1 = check_task_log_debounce(self.project_root, task1)
        self.assertFalse(result1)
        update_task_log_debounce(self.project_root, task1)
        
        result2 = check_task_log_debounce(self.project_root, task2)
        self.assertFalse(result2)
        update_task_log_debounce(self.project_root, task2)
        
        result3 = check_task_log_debounce(self.project_root, task3)
        self.assertFalse(result3)

    def test_update_overwrites_previous_lock(self):
        """Calling update again should overwrite the previous lock."""
        task1 = "Task 1"
        task2 = "Task 2"
        
        update_task_log_debounce(self.project_root, task1)
        self.assertTrue(check_task_log_debounce(self.project_root, task1))
        
        update_task_log_debounce(self.project_root, task2)
        self.assertFalse(check_task_log_debounce(self.project_root, task1))
        self.assertTrue(check_task_log_debounce(self.project_root, task2))


if __name__ == "__main__":
    unittest.main()
