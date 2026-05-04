"""Centralised .arms/ workspace path construction.

All modules should use WorkspacePaths instead of scattered os.path.join('.arms', ...) calls.
This eliminates the risk of typos and makes workspace layout changes a one-line update.
"""

import os


class WorkspacePaths:
    """Provides typed accessors for every file/dir inside the .arms/ workspace."""

    ARMS_DIR = ".arms"

    def __init__(self, project_root: str) -> None:
        self.root = project_root
        self.arms_dir = os.path.join(project_root, self.ARMS_DIR)

    # ── core state files ────────────────────────────────────────────────────

    @property
    def session(self) -> str:
        return os.path.join(self.arms_dir, "SESSION.md")

    @property
    def memory(self) -> str:
        return os.path.join(self.arms_dir, "MEMORY.md")

    @property
    def archive(self) -> str:
        return os.path.join(self.arms_dir, "SESSION_ARCHIVE.md")

    @property
    def brand(self) -> str:
        return os.path.join(self.arms_dir, "BRAND.md")

    @property
    def rules(self) -> str:
        return os.path.join(self.arms_dir, "RULES.md")

    @property
    def engine(self) -> str:
        return os.path.join(self.arms_dir, "ENGINE.md")

    @property
    def context_synthesis(self) -> str:
        return os.path.join(self.arms_dir, "CONTEXT_SYNTHESIS.md")

    @property
    def generated_prompts(self) -> str:
        return os.path.join(self.arms_dir, "GENERATED_PROMPTS.md")

    @property
    def history_summary(self) -> str:
        return os.path.join(self.arms_dir, "HISTORY_SUMMARY.md")

    # ── directories ─────────────────────────────────────────────────────────

    @property
    def reports_dir(self) -> str:
        return os.path.join(self.arms_dir, "reports")

    @property
    def outputs_dir(self) -> str:
        return os.path.join(self.arms_dir, "agent-outputs")

    @property
    def workflow_dir(self) -> str:
        return os.path.join(self.arms_dir, "workflow")

    # ── parameterised helpers ────────────────────────────────────────────────

    def workflow_file(self, filename: str) -> str:
        return os.path.join(self.arms_dir, "workflow", filename)

    def report_file(self, filename: str) -> str:
        return os.path.join(self.arms_dir, "reports", filename)

    def output_file(self, filename: str) -> str:
        return os.path.join(self.arms_dir, "agent-outputs", filename)
