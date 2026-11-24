"""
Day 29 Test Suite: Document Management Engine
Verifies multi-format extraction, incremental indexing with fingerprinting,
ranked keyword search, and safe dry-run organization with rollback capability.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.database import init_assistant_database, get_db_connection
from zye_personal_assistant.document_engine import DocumentEngine
from zye_personal_assistant.safety_gateway import SafetyGateway


class TestDocumentManagement(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_test_doc_")
        os.close(self._tmp_fd)
        self.db_path = Path(self._tmp_path)
        init_assistant_database(self.db_path)
        self.safety = SafetyGateway(db_path=self.db_path)
        self.engine = DocumentEngine(db_path=self.db_path, safety_gateway=self.safety)

        self.docs_dir = Path(tempfile.mkdtemp(prefix="zye_test_docs_"))
        (self.docs_dir / "sample_notes.txt").write_text(
            "Quarterly project review meeting notes with focus on artificial intelligence architecture.",
            encoding="utf-8",
        )
        (self.docs_dir / "metrics.csv").write_text(
            "metric,value,target\naccuracy,98.5,95.0\nlatency,120,200\n",
            encoding="utf-8",
        )
        (self.docs_dir / "readme.md").write_text(
            "# Zye Documentation\nThis markdown file describes the personal assistant sub-systems.",
            encoding="utf-8",
        )
        (self.docs_dir / "script.py").write_text(
            "# Python helper script\ndef run():\n    print('Zye Assistant Online')\n",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(str(self.docs_dir), ignore_errors=True)
        try:
            self.db_path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_index_folder_basic(self):
        """Indexes files and records their metadata and content snippets into SQLite."""
        res = self.engine.index_folder(str(self.docs_dir))
        self.assertEqual(res["status"], "SUCCESS")
        self.assertGreaterEqual(res["indexed_count"], 4)

        conn = get_db_connection(self.db_path)
        try:
            rows = conn.execute("SELECT * FROM doc_index;").fetchall()
            self.assertGreaterEqual(len(rows), 4)
            filenames = {r["filename"] for r in rows}
            self.assertIn("sample_notes.txt", filenames)
            self.assertIn("metrics.csv", filenames)
            self.assertIn("readme.md", filenames)
            self.assertIn("script.py", filenames)
        finally:
            conn.close()

    def test_02_incremental_indexing_skips_unchanged(self):
        """Second indexing pass without modifying files should skip unchanged files."""
        first_res = self.engine.index_folder(str(self.docs_dir))
        self.assertGreaterEqual(first_res["indexed_count"], 4)

        second_res = self.engine.index_folder(str(self.docs_dir))
        self.assertEqual(second_res["status"], "SUCCESS")
        self.assertGreaterEqual(second_res["skipped_unchanged"], 4)
        self.assertEqual(second_res["indexed_count"], 0)

    def test_03_search_documents(self):
        """Ranked search finds documents matching query in title or content snippet."""
        self.engine.index_folder(str(self.docs_dir))

        res1 = self.engine.search_documents("artificial intelligence")
        self.assertGreaterEqual(len(res1), 1)
        self.assertTrue(any("sample_notes.txt" in r["filename"] for r in res1))

        res2 = self.engine.search_documents("accuracy")
        self.assertGreaterEqual(len(res2), 1)
        self.assertTrue(any("metrics.csv" in r["filename"] for r in res2))

        res3 = self.engine.search_documents("sub-systems")
        self.assertGreaterEqual(len(res3), 1)
        self.assertTrue(any("readme.md" in r["filename"] for r in res3))

    def test_04_auto_organize_dry_run_safety(self):
        """Default dry_run=True must NOT move files, only preview planned moves."""
        txt_path = self.docs_dir / "sample_notes.txt"
        self.assertTrue(txt_path.exists())

        res = self.engine.auto_organize(str(self.docs_dir), dry_run=True)
        self.assertEqual(res["status"], "DRY_RUN_COMPLETED")
        self.assertTrue(res["dry_run"])
        self.assertGreaterEqual(res["planned_moves"], 4)

        # File remains in root folder
        self.assertTrue(txt_path.exists())

    def test_05_auto_organize_execution_and_rollback(self):
        """
        Confirmed auto_organize moves files into category subdirectories,
        and rollback restores them to their original location.
        """
        res = self.engine.auto_organize(str(self.docs_dir), dry_run=False, confirmed=True)
        self.assertEqual(res["status"], "ORGANIZATION_COMPLETED")
        self.assertGreaterEqual(res["files_moved"], 4)
        manifest_path = res["manifest_path"]
        self.assertTrue(Path(manifest_path).exists())

        # Original txt file should have moved to Notes_and_Text
        txt_orig = self.docs_dir / "sample_notes.txt"
        txt_dest = self.docs_dir / "Notes_and_Text" / "sample_notes.txt"
        self.assertFalse(txt_orig.exists())
        self.assertTrue(txt_dest.exists())

        # Execute Rollback
        rollback_res = self.engine.rollback_organization(manifest_path)
        self.assertEqual(rollback_res["status"], "ROLLBACK_COMPLETED")
        self.assertGreaterEqual(rollback_res["files_restored"], 4)

        # File is back at original path
        self.assertTrue(txt_orig.exists())


if __name__ == "__main__":
    unittest.main()
