"""Day 16 Unit Tests — Local File Search & Safe Opener."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from zye_windows.file_search import WindowsFileSearch


class TestWindowsFileSearch(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        # Create mock user directories
        self.desktop = self.root / "Desktop"
        self.desktop.mkdir()
        self.docs = self.root / "Documents"
        self.docs.mkdir()

        self.searcher = WindowsFileSearch()
        self.searcher.home = self.root

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_empty_query_error(self):
        res = self.searcher.find_and_open_local_file("")
        self.assertEqual(res["status"], "ERROR")

    def test_path_traversal_rejected(self):
        res_dotdot = self.searcher.find_and_open_local_file("../System32/cmd.exe")
        self.assertEqual(res_dotdot["status"], "REJECTED")

        res_slash = self.searcher.find_and_open_local_file("foo/bar")
        self.assertEqual(res_slash["status"], "REJECTED")

        res_backslash = self.searcher.find_and_open_local_file("foo\\bar")
        self.assertEqual(res_backslash["status"], "REJECTED")

    def test_file_not_found(self):
        res = self.searcher.find_and_open_local_file("completely_unknown_file.txt")
        self.assertEqual(res["status"], "NOT_FOUND")
        self.assertEqual(len(res["results"]), 0)

    def test_file_found_single_match(self):
        target = self.desktop / "test_report.pdf"
        target.write_text("dummy pdf content", encoding="utf-8")

        res = self.searcher.find_and_open_local_file("test_report")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(len(res["results"]), 1)
        self.assertEqual(res["results"][0]["filename"], "test_report.pdf")

    @patch("os.startfile")
    def test_file_open_single_match(self, mock_startfile):
        target = self.docs / "resume.docx"
        target.write_text("dummy resume content", encoding="utf-8")

        res = self.searcher.find_and_open_local_file("resume", open_file=True)
        self.assertEqual(res["status"], "OPENED")
        self.assertTrue(res["verified"])
        mock_startfile.assert_called_once()

    def test_multiple_matches_not_opened(self):
        (self.desktop / "project_a.txt").write_text("a", encoding="utf-8")
        (self.docs / "project_b.txt").write_text("b", encoding="utf-8")

        res = self.searcher.find_and_open_local_file("project", open_file=True)
        self.assertIn(res["status"], ("AMBIGUOUS_MATCH", "AMBIGUOUS_MATCHES"))
        self.assertEqual(len(res["results"]), 2)


if __name__ == "__main__":
    unittest.main()
