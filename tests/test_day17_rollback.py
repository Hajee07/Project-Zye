"""
Unit tests for Backup Rollback & Restoration Engine (Day 17).
Verifies atomic restore from verified backups, SHA-256 integrity verification,
post-rollback AST validation, and audit event history persistence.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zye_repair.backup_manager import ZyeBackupManager, calculate_sha256
from zye_repair.rollback_manager import ZyeRollbackManager


class TestDay17Rollback(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "zye_config.toml").write_text("# config\n", encoding="utf-8")
        self.backup_mgr = ZyeBackupManager(project_root=self.root)
        self.rollback_mgr = ZyeRollbackManager(project_root=self.root, backup_manager=self.backup_mgr)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_rollback_to_backup_success(self) -> None:
        """Verify rolling back mutated file restores original content and hash."""
        target = self.root / "app_logic.py"
        original_code = "def process():\n    return 'ORIGINAL_STABLE'\n"
        target.write_text(original_code, encoding="utf-8")
        orig_hash = calculate_sha256(target)

        # 1. Create backup
        b_res = self.backup_mgr.create_backup("app_logic.py", reason="Pre-mutation backup")
        self.assertEqual(b_res.get("status"), "SUCCESS")
        backup_id = b_res["backup_id"]

        # 2. Mutate / break file
        target.write_text("def process():\n    return 'BROKEN_CODE'\n", encoding="utf-8")
        self.assertNotEqual(calculate_sha256(target), orig_hash)

        # 3. Rollback
        rb_res = self.rollback_mgr.rollback_to_backup("app_logic.py", backup_id=backup_id)
        self.assertEqual(rb_res.get("status"), "SUCCESS")
        self.assertEqual(rb_res.get("restored_backup_id"), backup_id)
        self.assertEqual(rb_res.get("ast_validation"), "PASS")

        # 4. Verify on-disk file
        restored_code = target.read_text(encoding="utf-8")
        self.assertEqual(restored_code, original_code)
        self.assertEqual(calculate_sha256(target), orig_hash)

    def test_rollback_to_latest(self) -> None:
        """Verify rollback_to_latest automatically picks the newest backup."""
        target = self.root / "workflow.py"
        target.write_text("step = 1\n", encoding="utf-8")
        self.backup_mgr.create_backup("workflow.py", reason="v1")

        target.write_text("step = 2\n", encoding="utf-8")
        self.backup_mgr.create_backup("workflow.py", reason="v2")

        # Mutate to broken state
        target.write_text("step = 'BROKEN'\n", encoding="utf-8")

        # Rollback to latest (should be v2: step = 2)
        rb_res = self.rollback_mgr.rollback_to_latest("workflow.py")
        self.assertEqual(rb_res.get("status"), "SUCCESS")
        self.assertEqual(target.read_text(encoding="utf-8"), "step = 2\n")

    def test_rollback_history_logging(self) -> None:
        """Verify rollback actions are appended to logs/rollback_history.log."""
        target = self.root / "test_hist.py"
        target.write_text("x = 100\n", encoding="utf-8")
        b_res = self.backup_mgr.create_backup("test_hist.py", reason="Test history")
        target.write_text("x = 200\n", encoding="utf-8")

        self.rollback_mgr.rollback_to_backup("test_hist.py", backup_id=b_res["backup_id"])
        hist = self.rollback_mgr.get_rollback_history()
        self.assertTrue(len(hist) >= 1)
        self.assertEqual(hist[-1].get("action"), "rollback_to_backup")
        self.assertEqual(hist[-1].get("backup_id"), b_res["backup_id"])


if __name__ == "__main__":
    unittest.main()
