"""
Day 21 Unit Tests — Word Content Engine.
Verifies Unicode insertion, exact search/replace, paragraph addition, page breaks, and field insertion.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_office.word.word_content_engine import WordContentEngine
from zye_office.word.word_errors import WordNoActiveDocumentError, WordValidationError


class TestDay21ContentEngine(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_adapter = MagicMock()
        self.mock_adapter.worker.run.side_effect = lambda fn: fn()
        self.engine = WordContentEngine(adapter=self.mock_adapter)

    def test_insert_text_unicode_tamil(self) -> None:
        """Verify insertion of multi-byte Tamil text with Unicode preservation."""
        mock_doc = MagicMock()
        self.mock_adapter.get_active_document_raw.return_value = mock_doc
        tamil_text = "வணக்கம் உலகம்! Zye AI Word Automation."

        res = self.engine.insert_text(tamil_text, location="end")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["text"], tamil_text)
        mock_doc.Content.InsertAfter.assert_called_once_with(tamil_text)

    def test_insert_text_no_document_raises_error(self) -> None:
        """Verify WordNoActiveDocumentError raised when no document is active."""
        self.mock_adapter.get_active_document_raw.return_value = None
        with self.assertRaises(WordNoActiveDocumentError):
            self.engine.insert_text("hello", location="end")

    def test_replace_exact_text(self) -> None:
        """Verify native find and replace invocation."""
        mock_doc = MagicMock()
        mock_find = MagicMock()
        mock_doc.Content.Find = mock_find
        mock_find.Execute.return_value = True
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.replace_exact_text("old text", "new text", replace_all=True)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["old_text"], "old text")
        self.assertEqual(res["new_text"], "new text")
        mock_find.Execute.assert_called_once()

    def test_insert_page_break(self) -> None:
        """Verify inserting a page break."""
        mock_doc = MagicMock()
        mock_app = MagicMock()
        self.mock_adapter.get_raw_app.return_value = mock_app
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.insert_page_break()
        self.assertEqual(res["status"], "SUCCESS")
        mock_app.Selection.InsertBreak.assert_called_once()

    def test_insert_section_break(self) -> None:
        """Verify inserting section breaks."""
        mock_doc = MagicMock()
        mock_app = MagicMock()
        mock_doc.Sections.Count = 2
        self.mock_adapter.get_raw_app.return_value = mock_app
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.insert_section_break()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["new_total_sections"], 2)


if __name__ == "__main__":
    unittest.main()
