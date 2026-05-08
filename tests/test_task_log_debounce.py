"""Tests for task log debounce mechanism to prevent rapid duplicate calls from IDE."""

import json
import os
import tempfile
import time
import unittest

from arms_engine.paths import WorkspacePaths
from arms_engine.tasks import (
    build_task_log_signature,
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
        signature = build_task_log_signature(task="Create a feature")
        result = check_task_log_debounce(self.project_root, signature)
        self.assertFalse(result)

    def test_debounce_immediate_duplicate(self):
        """Immediate second call with same task should be debounced."""
        signature = build_task_log_signature(task="Create a feature")
        update_task_log_debounce(self.project_root, signature)
        result = check_task_log_debounce(self.project_root, signature)
        self.assertTrue(result)

    def test_debounce_case_insensitive(self):
        """Debounce matching is case-insensitive."""
        signature_lower = build_task_log_signature(task="create a feature")
        signature_upper = build_task_log_signature(task="CREATE A FEATURE")
        update_task_log_debounce(self.project_root, signature_lower)
        result = check_task_log_debounce(self.project_root, signature_upper)
        self.assertTrue(result)

    def test_no_debounce_different_task(self):
        """Different task should not be debounced."""
        signature1 = build_task_log_signature(task="Create a feature")
        signature2 = build_task_log_signature(task="Different task")
        update_task_log_debounce(self.project_root, signature1)
        result = check_task_log_debounce(self.project_root, signature2)
        self.assertFalse(result)

    def test_debounce_timeout(self):
        """Debounce should expire after timeout period."""
        signature = build_task_log_signature(task="Create a feature")
        update_task_log_debounce(self.project_root, signature)
        
        result_immediate = check_task_log_debounce(self.project_root, signature, debounce_seconds=1)
        self.assertTrue(result_immediate)
        
        time.sleep(1.1)
        result_after = check_task_log_debounce(self.project_root, signature, debounce_seconds=1)
        self.assertFalse(result_after)

    def test_debounce_lock_file_structure(self):
        """Lock file should contain signature and timestamp."""
        signature = build_task_log_signature(task="Create a feature")
        update_task_log_debounce(self.project_root, signature)
        
        lock_path = WorkspacePaths(self.project_root).task_log_lock
        self.assertTrue(os.path.exists(lock_path))
        
        with open(lock_path, "r") as f:
            lock_data = json.load(f)
        
        self.assertEqual(lock_data["signature"], signature)
        self.assertIn("timestamp", lock_data)
        self.assertIsInstance(lock_data["timestamp"], (int, float))

    def test_debounce_malformed_lock_file(self):
        """Malformed lock file should not crash debounce check."""
        lock_path = WorkspacePaths(self.project_root).task_log_lock
        with open(lock_path, "w") as f:
            f.write("invalid json {")
        
        signature = build_task_log_signature(task="Task")
        result = check_task_log_debounce(self.project_root, signature)
        self.assertFalse(result)

    def test_concurrent_task_debounce(self):
        """Rapid calls with different tasks should all be allowed."""
        signature1 = build_task_log_signature(task="Task 1")
        signature2 = build_task_log_signature(task="Task 2")
        signature3 = build_task_log_signature(task="Task 3")
        
        result1 = check_task_log_debounce(self.project_root, signature1)
        self.assertFalse(result1)
        update_task_log_debounce(self.project_root, signature1)
        
        result2 = check_task_log_debounce(self.project_root, signature2)
        self.assertFalse(result2)
        update_task_log_debounce(self.project_root, signature2)
        
        result3 = check_task_log_debounce(self.project_root, signature3)
        self.assertFalse(result3)

    def test_update_overwrites_previous_lock(self):
        """Calling update again should overwrite the previous lock."""
        signature1 = build_task_log_signature(task="Task 1")
        signature2 = build_task_log_signature(task="Task 2")
        
        update_task_log_debounce(self.project_root, signature1)
        self.assertTrue(check_task_log_debounce(self.project_root, signature1))
        
        update_task_log_debounce(self.project_root, signature2)
        self.assertFalse(check_task_log_debounce(self.project_root, signature1))
        self.assertTrue(check_task_log_debounce(self.project_root, signature2))

    def test_same_task_different_status_not_debounced(self):
        """Same task text with changed metadata must not be debounced."""
        pending_signature = build_task_log_signature(task="Task 1", status="Pending")
        in_progress_signature = build_task_log_signature(task="Task 1", status="In Progress")

        update_task_log_debounce(self.project_root, pending_signature)
        self.assertFalse(check_task_log_debounce(self.project_root, in_progress_signature))


if __name__ == "__main__":
    unittest.main()
