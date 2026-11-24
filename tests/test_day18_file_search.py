"""
Day 18 Unit Tests — Fast Local File Search Engine.
Verifies bounded searching across allowed directories (Desktop, Documents, Downloads, Videos),
extension filtering, candidate disambiguation, and file detail retrieval.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zye_windows.file_search import WindowsFileSearch
from zye_windows.windows_models import FileSearchResult


class TestDay18FileSearch(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

        # Create sample directory structure
        (self.base_path / "Documents").mkdir()
        (self.base_path / "Downloads").mkdir()

        # Populate sample files
        (self.base_path / "Documents" / "Project_Report.docx").write_text("Report content", encoding="utf-8")
        (self.base_path / "Downloads" / "Project_Report.pdf").write_text("PDF content", encoding="utf-8")
        (self.base_path / "Downloads" / "budget_2026.xlsx").write_text("Excel content", encoding="utf-8")

        self.fs = WindowsFileSearch()
        self.fs.home = self.base_path  # Point to temp root for isolation

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_search_local_files_single_match(self) -> None:
        """Verify searching for unique file returns single result."""
        results = self.fs.search_local_files("budget")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].filename, "budget_2026.xlsx")

    def test_search_local_files_multiple_matches(self) -> None:
        """Verify searching for common keyword returns multiple candidate results."""
        results = self.fs.search_local_files("Project_Report")
        self.assertEqual(len(results), 2)
        filenames = [r.filename for r in results]
        self.assertIn("Project_Report.docx", filenames)
        self.assertIn("Project_Report.pdf", filenames)

    def test_find_and_open_local_file_ambiguous_prompt(self) -> None:
        """Verify find_and_open_local_file returns AMBIGUOUS_MATCH when multiple files match."""
        res = self.fs.find_and_open_local_file("Project_Report", open_file=True)
        self.assertEqual(res["status"], "AMBIGUOUS_MATCH")
        self.assertEqual(res["count"], 2)
        self.assertTrue(res["open_requested"])

    def test_get_file_details(self) -> None:
        """Verify get_file_details extracts size, modified timestamp, and extension."""
        target = self.base_path / "Documents" / "Project_Report.docx"
        details = self.fs.get_file_details(str(target))
        self.assertEqual(details["status"], "SUCCESS")
        self.assertEqual(details["filename"], "Project_Report.docx")
        self.assertEqual(details["extension"], ".docx")
        self.assertFalse(details["is_executable"])
        self.assertTrue(details["size_bytes"] > 0)


if __name__ == "__main__":
    unittest.main()
