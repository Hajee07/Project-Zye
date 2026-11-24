"""
Day 21 Unit Tests — Word Table of Contents (TOC) Engine.
Verifies TOC insertion, heading hierarchy inspection, field updating, and heading depth bounds (1..9).
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_office.word.word_errors import WordNoActiveDocumentError, WordValidationError
from zye_office.word.word_toc_engine import WordTOCEngine


class TestDay21TOC(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_adapter = MagicMock()
        self.mock_adapter.worker.run.side_effect = lambda fn: fn()
        self.engine = WordTOCEngine(adapter=self.mock_adapter)

    def test_inspect_heading_hierarchy(self) -> None:
        """Verify inspecting headings in active document."""
        mock_doc = MagicMock()
        mock_p1 = MagicMock()
        mock_p1.Range.Style.NameLocal = "Heading 1"
        mock_p1.Range.Text = "Introduction\r"

        mock_p2 = MagicMock()
        mock_p2.Range.Style.NameLocal = "Heading 2"
        mock_p2.Range.Text = "System Architecture\r"

        mock_doc.Paragraphs = [mock_p1, mock_p2]
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.inspect_heading_hierarchy()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["heading_count"], 2)
        self.assertEqual(res["headings"][0]["text"], "Introduction")
        self.assertEqual(res["headings"][1]["level"], 2)

    def test_insert_toc_success(self) -> None:
        """Verify Table of Contents insertion with valid heading depth."""
        mock_doc = MagicMock()
        mock_range = MagicMock()
        mock_doc.TablesOfContents.Add.return_value = MagicMock()
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.insert_table_of_contents(upper_level=1, lower_level=3)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["upper_level"], 1)
        self.assertEqual(res["lower_level"], 3)
        mock_doc.TablesOfContents.Add.assert_called_once()

    def test_insert_toc_invalid_levels_raises_error(self) -> None:
        """Verify invalid heading level combinations raise WordValidationError."""
        with self.assertRaises(WordValidationError):
            self.engine.insert_table_of_contents(upper_level=4, lower_level=2)

        with self.assertRaises(WordValidationError):
            self.engine.insert_table_of_contents(upper_level=0, lower_level=3)

    def test_update_toc(self) -> None:
        """Verify TOC fields refresh."""
        mock_doc = MagicMock()
        mock_toc = MagicMock()
        mock_doc.TablesOfContents.Count = 1
        mock_doc.TablesOfContents.return_value = mock_toc
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.update_table_of_contents()
        self.assertEqual(res["status"], "SUCCESS")
        mock_toc.Update.assert_called_once()


if __name__ == "__main__":
    unittest.main()
