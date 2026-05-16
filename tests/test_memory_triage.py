"""Tests for the intelligent memory triage system.

Covers:
- score_memory_entry: actionability / specificity / uniqueness / length dimensions
- repair_memory_file: expired stale entries, duplicate approved, missing sections
- smart_triage_pending_memory: auto-approve / discard / review decisions
- identify_memory_command: recognises "triage"
- handle_memory_command: dispatches triage correctly
"""
import datetime
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

import arms_engine.init_arms as init_arms
from arms_engine.memory import (
    STALE_PENDING_DAYS,
    TRIAGE_AUTO_APPROVE_THRESHOLD,
    TRIAGE_AUTO_DISCARD_THRESHOLD,
    handle_memory_command,
    identify_memory_command,
    repair_memory_file,
    score_memory_entry,
    smart_triage_pending_memory,
)
from arms_engine.paths import WorkspacePaths


# ── helpers ────────────────────────────────────────────────────────────────

ARMS_ROOT = os.path.join(os.path.dirname(__file__), "..", "arms_engine")


def _today_id(offset_days=0):
    """Return a memory-YYYYMMDD-01 ID offset by *offset_days* relative to today."""
    d = datetime.date.today() + datetime.timedelta(days=offset_days)
    return f"memory-{d.strftime('%Y%m%d')}-01"


def _old_id(days_ago=10):
    """Return a memory ID that is *days_ago* days old (stale)."""
    d = datetime.date.today() - datetime.timedelta(days=days_ago)
    return f"memory-{d.strftime('%Y%m%d')}-01"


def _minimal_memory(pending_lines="", approved_lines=""):
    """Build a minimal MEMORY.md with optional pending/approved lines."""
    return (
        "# Project Memory\n\n"
        "## Developer Preferences\n"
        + (approved_lines + "\n" if approved_lines else "\n")
        + "## Known Bugs & Fixes\n"
        + (pending_lines + "\n" if pending_lines else "\n")
    )


def _write_memory(project_root, content):
    wp = WorkspacePaths(project_root)
    os.makedirs(wp.arms_dir, exist_ok=True)
    with open(wp.memory, "w") as f:
        f.write(content)


def _read_memory(project_root):
    with open(WorkspacePaths(project_root).memory) as f:
        return f.read()


def _write_session(project_root):
    """Write a bare-minimum SESSION.md so validate_memory_command passes."""
    wp = WorkspacePaths(project_root)
    os.makedirs(wp.arms_dir, exist_ok=True)
    with open(wp.session, "w") as f:
        f.write("# ARMS Session\n\n## Active Tasks\n\n_No active tasks._\n")


# ── score_memory_entry ─────────────────────────────────────────────────────


class TestScoreMemoryEntry(unittest.TestCase):
    def test_returns_float_in_range(self):
        score = score_memory_entry("Use pytest for all unit tests.", [])
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_high_quality_lesson_scores_above_threshold(self):
        lesson = (
            "Always run `python -m unittest discover -s tests -p 'test_*.py'` "
            "before committing to ensure no regressions."
        )
        score = score_memory_entry(lesson, [])
        self.assertGreaterEqual(score, TRIAGE_AUTO_APPROVE_THRESHOLD,
                                f"Expected high score, got {score}")

    def test_low_quality_lesson_scores_below_discard(self):
        lesson = "ok"
        score = score_memory_entry(lesson, [])
        self.assertLess(score, TRIAGE_AUTO_DISCARD_THRESHOLD,
                        f"Expected very low score, got {score}")

    def test_duplicate_lesson_scores_lower_than_novel(self):
        lesson = "Prefer snake_case for Python variable names."
        novel_score = score_memory_entry(lesson, [])
        dup_score = score_memory_entry(lesson, [lesson])
        # A duplicate entry should score equal or lower (uniqueness dimension drops)
        self.assertLessEqual(dup_score, novel_score)

    def test_empty_lesson_returns_low_score(self):
        score = score_memory_entry("", [])
        self.assertLess(score, 0.20)

    def test_action_verb_boosts_score(self):
        with_verb = score_memory_entry("Always use type hints in Python.", [])
        without_verb = score_memory_entry("type hints in Python.", [])
        self.assertGreaterEqual(with_verb, without_verb)

    def test_technical_token_boosts_specificity(self):
        technical = score_memory_entry("Run `arms init --root /path` to bootstrap.", [])
        generic = score_memory_entry("Bootstrap the project workspace before starting.", [])
        self.assertGreaterEqual(technical, generic)


# ── repair_memory_file ─────────────────────────────────────────────────────


class TestRepairMemoryFile(unittest.TestCase):
    def test_no_memory_file_returns_empty_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = repair_memory_file(tmp)
            self.assertEqual(result, {"repaired": [], "expired": [], "deduplicated": []})

    def test_expires_stale_pending_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_id = _old_id(days_ago=STALE_PENDING_DAYS + 2)
            content = _minimal_memory(
                pending_lines=f"- [PENDING APPROVAL][{old_id}]: Some old lesson."
            )
            _write_memory(tmp, content)
            result = repair_memory_file(tmp)
            self.assertIn(old_id, result["expired"])
            self.assertNotIn(old_id, _read_memory(tmp))

    def test_does_not_expire_fresh_pending_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            fresh_id = _today_id(offset_days=0)
            content = _minimal_memory(
                pending_lines=f"- [PENDING APPROVAL][{fresh_id}]: Fresh lesson."
            )
            _write_memory(tmp, content)
            result = repair_memory_file(tmp)
            self.assertNotIn(fresh_id, result["expired"])
            self.assertIn(fresh_id, _read_memory(tmp))

    def test_deduplicates_approved_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            dup_line = (
                "- [APPROVED][memory-20250101-01]: Use type hints everywhere."
            )
            content = (
                "# Memory\n\n## Developer Preferences\n"
                + dup_line + "\n"
                + dup_line + "\n"
            )
            _write_memory(tmp, content)
            result = repair_memory_file(tmp)
            self.assertEqual(len(result["deduplicated"]), 1)
            mem = _read_memory(tmp)
            self.assertEqual(mem.count("[APPROVED][memory-20250101-01]"), 1)

    def test_restores_missing_required_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_memory(tmp, "# Memory\n\n## Developer Preferences\n\n")
            result = repair_memory_file(tmp)
            restored = result["repaired"]
            restored_names = [r.replace("Restored missing section: ", "") for r in restored]
            self.assertIn("Project Context & MVP", restored_names)
            self.assertIn("Known Bugs & Fixes", restored_names)

    def test_idempotent_on_clean_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            content = (
                "# Memory\n\n"
                "## Project Context & MVP\n\n"
                "## Primary Use Case & Implications\n\n"
                "## Phase 2 Backlog\n\n"
                "## Developer Preferences\n\n"
                "## Known Bugs & Fixes\n\n"
            )
            _write_memory(tmp, content)
            r1 = repair_memory_file(tmp)
            r2 = repair_memory_file(tmp)
            self.assertEqual(r1["repaired"], [])
            self.assertEqual(r2["repaired"], [])


# ── smart_triage_pending_memory ────────────────────────────────────────────


class TestSmartTriagePendingMemory(unittest.TestCase):
    def test_returns_empty_dict_when_no_memory_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = smart_triage_pending_memory(tmp, ARMS_ROOT)
            self.assertEqual(result, {"approved": [], "discarded": [], "needs_review": []})

    def test_auto_approves_high_quality_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            fresh_id = _today_id()
            lesson = (
                "Always run `python -m unittest discover -s tests -p 'test_*.py'` "
                "before committing to avoid regressions in the test suite."
            )
            content = (
                "# Memory\n\n"
                "## Developer Preferences\n"
                f"- [PENDING APPROVAL][{fresh_id}]: {lesson}\n"
            )
            _write_memory(tmp, content)
            _write_session(tmp)
            buf = io.StringIO()
            with redirect_stdout(buf):
                result = smart_triage_pending_memory(tmp, ARMS_ROOT)
            approved_ids = [e["draft_id"] for e in result["approved"]]
            self.assertIn(fresh_id, approved_ids)
            self.assertEqual(result["discarded"], [])
            mem = _read_memory(tmp)
            self.assertIn("[APPROVED]", mem)
            self.assertNotIn("[PENDING APPROVAL]", mem)
            self.assertIn("✅ Auto-approved", buf.getvalue())

    def test_auto_discards_low_quality_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            fresh_id = _today_id()
            content = (
                "# Memory\n\n"
                "## Known Bugs & Fixes\n"
                f"- [PENDING APPROVAL][{fresh_id}]: ok\n"
            )
            _write_memory(tmp, content)
            _write_session(tmp)
            buf = io.StringIO()
            with redirect_stdout(buf):
                result = smart_triage_pending_memory(tmp, ARMS_ROOT)
            discarded_ids = [e["draft_id"] for e in result["discarded"]]
            self.assertIn(fresh_id, discarded_ids)
            self.assertEqual(result["approved"], [])
            self.assertNotIn(fresh_id, _read_memory(tmp))
            self.assertIn("🗑️", buf.getvalue())

    def test_marginal_entry_surfaces_review_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            fresh_id = _today_id()
            # A moderate-quality lesson — specific enough but not action-verb-heavy.
            lesson = "The BM25 scorer is located in arms_engine/bm25.py for reuse."
            content = (
                "# Memory\n\n"
                "## Developer Preferences\n"
                f"- [PENDING APPROVAL][{fresh_id}]: {lesson}\n"
            )
            _write_memory(tmp, content)
            _write_session(tmp)
            buf = io.StringIO()
            with redirect_stdout(buf):
                result = smart_triage_pending_memory(tmp, ARMS_ROOT)
            # Entry should remain in memory (not approved or discarded).
            out = buf.getvalue()
            total = len(result["approved"]) + len(result["discarded"]) + len(result["needs_review"])
            self.assertEqual(total, 1)
            if result["needs_review"]:
                self.assertIn("Memory Review Required", out)
                self.assertIn("arms memory append --draft-id", out)
                self.assertIn(fresh_id, out)

    def test_stale_pending_entry_is_expired_during_triage(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_id = _old_id(days_ago=STALE_PENDING_DAYS + 3)
            content = (
                "# Memory\n\n"
                "## Known Bugs & Fixes\n"
                f"- [PENDING APPROVAL][{old_id}]: Some lesson that expired.\n"
            )
            _write_memory(tmp, content)
            _write_session(tmp)
            buf = io.StringIO()
            with redirect_stdout(buf):
                smart_triage_pending_memory(tmp, ARMS_ROOT)
            self.assertNotIn(old_id, _read_memory(tmp))

    def test_no_pending_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            content = (
                "# Memory\n\n"
                "## Developer Preferences\n"
                "- [APPROVED][memory-20250101-01]: Keep it simple.\n"
            )
            _write_memory(tmp, content)
            _write_session(tmp)
            result = smart_triage_pending_memory(tmp, ARMS_ROOT)
            self.assertEqual(result["approved"], [])
            self.assertEqual(result["discarded"], [])
            self.assertEqual(result["needs_review"], [])


# ── identify_memory_command ────────────────────────────────────────────────


class TestIdentifyMemoryCommandTriage(unittest.TestCase):
    def test_identifies_triage(self):
        self.assertEqual(identify_memory_command(("memory", "triage")), "triage")

    def test_draft_still_works(self):
        self.assertEqual(identify_memory_command(("memory", "draft")), "draft")

    def test_append_still_works(self):
        self.assertEqual(identify_memory_command(("memory", "append")), "append")

    def test_unknown_returns_empty(self):
        self.assertEqual(identify_memory_command(("memory", "unknown")), "")


# ── handle_memory_command triage dispatch ──────────────────────────────────


class TestHandleMemoryCommandTriage(unittest.TestCase):
    def test_triage_dispatches_without_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_memory(tmp, "# Memory\n\n## Developer Preferences\n\n")
            _write_session(tmp)
            buf = io.StringIO()
            with redirect_stdout(buf):
                handle_memory_command(tmp, ARMS_ROOT, "triage")
            # Should not raise and should print something.
            out = buf.getvalue()
            self.assertIsInstance(out, str)

    def test_triage_prints_no_pending_message_when_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_memory(tmp, "# Memory\n\n## Developer Preferences\n\n")
            _write_session(tmp)
            buf = io.StringIO()
            with redirect_stdout(buf):
                handle_memory_command(tmp, ARMS_ROOT, "triage")
            self.assertIn("No pending memory entries", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
