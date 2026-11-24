"""
Day 21 Unit Tests — Word Bookmark Engine.
Verifies named bookmark creation, identifier validation, bookmark enumeration, and bookmark deletion.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_office.word.word_bookmark_engine import WordBookmarkEngine
from zye_office.word.word_errors import WordNoActiveDocumentError, WordValidationError


class TestDay21Bookmarks(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_adapter = MagicMock()
        self.mock_adapter.worker.run.side_effect = lambda fn: fn()
        self.engine = WordBookmarkEngine(adapter=self.mock_adapter)

    def test_create_bookmark_valid_name(self) -> None:
        """Verify bookmark creation with valid alphanumeric name."""
        mock_doc = MagicMock()
        mock_app = MagicMock()
        mock_bms = MagicMock()
        mock_doc.Bookmarks = mock_bms
        self.mock_adapter.get_raw_app.return_value = mock_app
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.create_bookmark(name="Section_Overview_01")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["bookmark_name"], "Section_Overview_01")
        mock_bms.Add.assert_called_once()

    def test_create_bookmark_invalid_name_spaces(self) -> None:
        """Verify bookmark names with spaces or illegal characters raise WordValidationError."""
        with self.assertRaises(WordValidationError):
            self.engine.create_bookmark(name="Invalid Name With Spaces")

        with self.assertRaises(WordValidationError):
            self.engine.create_bookmark(name="123_Starts_With_Number")

    def test_get_document_bookmarks(self) -> None:
        """Verify listing bookmarks in document."""
        mock_doc = MagicMock()
        mock_bm = MagicMock()
        mock_bm.Name = "IntroSection"
        mock_bm.Range.Start = 0
        mock_bm.Range.End = 50
        mock_doc.Bookmarks = [mock_bm]
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.get_document_bookmarks()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["count"], 1)
        self.assertEqual(res["bookmarks"][0]["name"], "IntroSection")

    def test_delete_bookmark(self) -> None:
        """Verify bookmark deletion."""
        mock_doc = MagicMock()
        mock_bm = MagicMock()
        mock_doc.Bookmarks.Exists.return_value = True
        mock_doc.Bookmarks.return_value = mock_bm
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.delete_bookmark(name="IntroSection")
        self.assertEqual(res["status"], "SUCCESS")
        mock_bm.Delete.assert_called_once()


if __name__ == "__main__":
    unittest.main()
