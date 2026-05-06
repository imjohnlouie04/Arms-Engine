"""Tests for startup task deduplication logic."""

import unittest
from arms_engine.tables import (
    deduplicate_startup_tasks_against_existing,
    merge_task_tables,
    parse_task_rows,
)


class StartupTaskDedupTests(unittest.TestCase):
    """Ensure startup tasks don't duplicate when SESSION.md is updated multiple times."""

    def test_deduplicate_removes_matching_tasks(self):
        """When startup tasks match existing tasks, only new ones are returned."""
        startup = (
            "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
            "|---|------|----------------|--------------|--------------|--------|\n"
            "| 1 | Create charter | arms-product-agent | — | — | Pending |\n"
            "| 2 | Scaffold Next.js | arms-devops-agent | devops-orchestrator | #1 | Pending |\n"
            "| 3 | Design UI | arms-frontend-agent | frontend-design | #1, #2 | Pending |"
        )
        existing = (
            "## Active Tasks\n"
            "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
            "|---|------|----------------|--------------|--------------|--------|\n"
            "| 1 | Create charter | arms-product-agent | — | — | Pending |\n"
            "| 2 | Scaffold Next.js | arms-devops-agent | devops-orchestrator | #1 | Pending |"
        )
        result = deduplicate_startup_tasks_against_existing(startup, existing)
        rows = parse_task_rows(result)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Task"], "Design UI")

    def test_deduplicate_case_insensitive(self):
        """Task matching is case-insensitive and whitespace-normalized."""
        startup = (
            "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
            "|---|------|----------------|--------------|--------------|--------|\n"
            "| 1 | Create  A  Product  Charter | arms-product-agent | — | — | Pending |"
        )
        existing = (
            "## Active Tasks\n"
            "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
            "|---|------|----------------|--------------|--------------|--------|\n"
            "| 1 | create a product charter | arms-product-agent | — | — | Pending |"
        )
        result = deduplicate_startup_tasks_against_existing(startup, existing)
        self.assertEqual(result, "")

    def test_deduplicate_returns_empty_when_all_match(self):
        """When all startup tasks exist, returns empty string."""
        startup = (
            "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
            "|---|------|----------------|--------------|--------------|--------|\n"
            "| 1 | Task A | agent-1 | — | — | Pending |"
        )
        existing = (
            "## Active Tasks\n"
            "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
            "|---|------|----------------|--------------|--------------|--------|\n"
            "| 1 | Task A | agent-1 | — | — | Pending |"
        )
        result = deduplicate_startup_tasks_against_existing(startup, existing)
        self.assertEqual(result, "")

    def test_deduplicate_returns_original_when_no_matches(self):
        """When no startup tasks match, returns original content."""
        startup = (
            "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
            "|---|------|----------------|--------------|--------------|--------|\n"
            "| 1 | Task A | agent-1 | — | — | Pending |"
        )
        existing = (
            "## Active Tasks\n"
            "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
            "|---|------|----------------|--------------|--------------|--------|\n"
            "| 1 | Task B | agent-2 | — | — | Pending |"
        )
        result = deduplicate_startup_tasks_against_existing(startup, existing)
        self.assertEqual(result, startup)

    def test_merge_appends_new_tasks_and_renumbers(self):
        """merge_task_tables appends new rows and renumbers all of them."""
        existing = (
            "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
            "|---|------|----------------|--------------|--------------|--------|\n"
            "| 1 | Task A | agent-1 | skill-1 | — | Pending |\n"
            "| 2 | Task B | agent-2 | — | #1 | Pending |"
        )
        new = (
            "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
            "|---|------|----------------|--------------|--------------|--------|\n"
            "| 1 | Task C | agent-3 | — | — | Pending |"
        )
        result = merge_task_tables(existing, new)
        rows = parse_task_rows(result)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["#"], "1")
        self.assertEqual(rows[0]["Task"], "Task A")
        self.assertEqual(rows[1]["#"], "2")
        self.assertEqual(rows[1]["Task"], "Task B")
        self.assertEqual(rows[2]["#"], "3")
        self.assertEqual(rows[2]["Task"], "Task C")

    def test_merge_handles_empty_new_table(self):
        """merge_task_tables returns existing table if new table is empty."""
        existing = (
            "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
            "|---|------|----------------|--------------|--------------|--------|\n"
            "| 1 | Task A | agent-1 | — | — | Pending |"
        )
        result = merge_task_tables(existing, "")
        self.assertEqual(result, existing)

    def test_merge_handles_empty_existing_table(self):
        """merge_task_tables returns new table if existing table is empty."""
        new = (
            "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
            "|---|------|----------------|--------------|--------------|--------|\n"
            "| 1 | Task A | agent-1 | — | — | Pending |"
        )
        result = merge_task_tables("", new)
        self.assertEqual(result, new)

    def test_deduplicate_and_merge_workflow(self):
        """Full workflow: deduplicate startup tasks, then merge new ones."""
        startup = (
            "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
            "|---|------|----------------|--------------|--------------|--------|\n"
            "| 1 | Create charter | arms-product-agent | — | — | Pending |\n"
            "| 2 | Scaffold Next.js | arms-devops-agent | devops-orchestrator | #1 | Pending |\n"
            "| 3 | Design UI | arms-frontend-agent | frontend-design | #1, #2 | Pending |"
        )
        existing = (
            "## Active Tasks\n"
            "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
            "|---|------|----------------|--------------|--------------|--------|\n"
            "| 1 | Create charter | arms-product-agent | — | — | Pending |\n"
            "| 2 | Scaffold Next.js | arms-devops-agent | devops-orchestrator | #1 | Pending |"
        )
        existing_table = (
            "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
            "|---|------|----------------|--------------|--------------|--------|\n"
            "| 1 | Create charter | arms-product-agent | — | — | Pending |\n"
            "| 2 | Scaffold Next.js | arms-devops-agent | devops-orchestrator | #1 | Pending |"
        )

        dedup_result = deduplicate_startup_tasks_against_existing(startup, existing)
        merged = merge_task_tables(existing_table, dedup_result)

        rows = parse_task_rows(merged)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["Task"], "Create charter")
        self.assertEqual(rows[1]["Task"], "Scaffold Next.js")
        self.assertEqual(rows[2]["Task"], "Design UI")
        self.assertEqual(rows[2]["#"], "3")


if __name__ == "__main__":
    unittest.main()
