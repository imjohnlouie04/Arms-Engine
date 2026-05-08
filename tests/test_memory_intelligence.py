import io
import json
import os
import sys
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from arms_engine import init_arms
from arms_engine import session as session_module


REPO_ROOT = Path(__file__).resolve().parents[1]
ARMS_ROOT = REPO_ROOT / "arms_engine"


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class MemoryIntelligenceTests(unittest.TestCase):
    def invoke_cli(self, cwd, *args):
        stdout = io.StringIO()
        exit_code = 0
        with working_directory(cwd), mock.patch.object(sys, "argv", ["arms", *args]), redirect_stdout(stdout):
            try:
                init_arms.main()
            except SystemExit as exc:
                exit_code = exc.code if isinstance(exc.code, int) else 1
        return exit_code, stdout.getvalue()

    def test_update_session_compiles_memory_index(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "README.md").write_text("# Demo\nMemory intelligence.\n", encoding="utf-8")
            self.invoke_cli(project_root, "init", "yolo", "--root", str(ARMS_ROOT))

            (project_root / ".arms" / "MEMORY.md").write_text(
                "\n".join(
                    [
                        "# ARMS Project Memory",
                        "",
                        "## Developer Preferences",
                        "- [APPROVED][memory-20260507-01]: Prefer strict task intake before implementation.",
                        "",
                        "## Known Bugs & Fixes",
                        "- [PENDING APPROVAL][memory-20260507-02]: Investigate hydration mismatch in verse page.",
                    ]
                ),
                encoding="utf-8",
            )

            init_arms.update_session(str(project_root), str(ARMS_ROOT), yolo=True)

            index_path = project_root / ".arms" / "memory-index.json"
            self.assertTrue(index_path.exists())
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["version"], session_module.MEMORY_INDEX_VERSION)
            self.assertGreaterEqual(len(payload["entries"]), 2)

    def test_memory_packet_excludes_pending_entries(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".arms").mkdir()
            (project_root / ".arms" / "MEMORY.md").write_text(
                "\n".join(
                    [
                        "# ARMS Project Memory",
                        "",
                        "## Known Bugs & Fixes",
                        "- [PENDING APPROVAL][memory-20260507-01]: Pending token fix note.",
                        "- [APPROVED][memory-20260507-02]: Token refresh must rotate session secrets.",
                    ]
                ),
                encoding="utf-8",
            )
            rows = [
                {
                    "task": "Fix token refresh expiry bug",
                    "agent": "arms-backend-agent",
                    "skill": "backend-system-architect",
                    "dependencies": "—",
                    "status": "Blocked",
                }
            ]
            packet = session_module.render_memory_packet(str(project_root), rows, blockers_text="token refresh expiry")
            self.assertIn("Token refresh must rotate session secrets", packet)
            self.assertNotIn("Pending token fix note", packet)

    def test_memory_packet_prioritizes_relevant_entries(self):
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".arms").mkdir()
            (project_root / ".arms" / "MEMORY.md").write_text(
                "\n".join(
                    [
                        "# ARMS Project Memory",
                        "",
                        "## Developer Preferences",
                        "- [APPROVED][memory-20260507-01]: Use single quotes in tests where possible.",
                        "",
                        "## Known Bugs & Fixes",
                        "- [APPROVED][memory-20260507-02]: Token refresh race is fixed by rotating secrets and updating expiry atomically.",
                    ]
                ),
                encoding="utf-8",
            )
            rows = [
                {
                    "task": "Fix token refresh race for mobile sessions",
                    "agent": "arms-backend-agent",
                    "skill": "backend-system-architect",
                    "dependencies": "—",
                    "status": "Blocked",
                }
            ]
            packet = session_module.render_memory_packet(str(project_root), rows, blockers_text="token refresh race")
            lines = [line for line in packet.splitlines() if line.startswith("- [")]
            self.assertTrue(lines)
            self.assertIn("Known Bugs & Fixes", lines[0])
            self.assertIn("Token refresh race", lines[0])


if __name__ == "__main__":
    unittest.main()

