"""
Unit tests for Day 14 Document Management Engine.
Verifies multi-format indexing, keyword search, safe auto-organization, and rollback.
"""

import os
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.document_engine import DocumentEngine
from zye_personal_assistant.safety_gateway import SafetyGateway


class TestDay14Documents(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_doc_test_")
        os.close(self._tmp_fd)
        sg = SafetyGateway(db_path=self._tmp_path)
        self.engine = DocumentEngine(db_path=self._tmp_path, safety_gateway=sg)
        self.test_dir = tempfile.mkdtemp(prefix="zye_docs_")

        # Create sample documents
        Path(self.test_dir, "report.txt").write_text("Quarterly engineering performance summary.", encoding="utf-8")
        Path(self.test_dir, "notes.md").write_text("# Project Roadmap\nMilestones and architecture guidelines.", encoding="utf-8")
        Path(self.test_dir, "financials.csv").write_text("item,cost\nserver,500\nlicense,200", encoding="utf-8")

    def tearDown(self):
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
            import shutil
            shutil.rmtree(self.test_dir, ignore_errors=True)
        except Exception:
            pass

    def test_01_index_folder(self):
        res = self.engine.index_folder(self.test_dir)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["indexed_files"], 3)

    def test_02_search_documents(self):
        self.engine.index_folder(self.test_dir)
        matches = self.engine.search_documents("engineering")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["filename"], "report.txt")
        self.assertIn("Quarterly", matches[0]["snippet"])

    def test_03_auto_organize_dry_run(self):
        plan = self.engine.auto_organize(self.test_dir, dry_run=True)
        self.assertEqual(plan["status"], "DRY_RUN")
        self.assertEqual(plan["planned_moves_count"], 3)
        self.assertIn("safety_audit", plan)

    def test_04_auto_organize_execution_and_rollback(self):
        # Execute moves
        exec_res = self.engine.auto_organize(self.test_dir, dry_run=False)
        self.assertEqual(exec_res["status"], "SUCCESS")
        self.assertEqual(exec_res["executed_moves_count"], 3)

        # Verify files moved into subfolders
        self.assertTrue(Path(self.test_dir, "Notes_and_Text", "report.txt").exists())
        self.assertTrue(Path(self.test_dir, "Spreadsheets", "financials.csv").exists())

        # Rollback
        rb_res = self.engine.rollback_last_organization()
        self.assertEqual(rb_res["status"], "SUCCESS")
        self.assertEqual(rb_res["rolled_back_count"], 3)

        # Verify files returned to original location
        self.assertTrue(Path(self.test_dir, "report.txt").exists())
        self.assertTrue(Path(self.test_dir, "financials.csv").exists())


if __name__ == "__main__":
    unittest.main()
