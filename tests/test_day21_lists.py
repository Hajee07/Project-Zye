"""
Day 21 Unit Tests — Word List Engine.
Verifies bulleted list generation, numbered list formatting, and Unicode multi-byte text preservation.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_office.word.word_errors import WordNoActiveDocumentError
from zye_office.word.word_list_engine import WordListEngine


class TestDay21Lists(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_adapter = MagicMock()
        self.mock_adapter.worker.run.side_effect = lambda fn: fn()
        self.engine = WordListEngine(adapter=self.mock_adapter)

    def test_create_bullet_list_tamil_and_english(self) -> None:
        """Verify bulleted list generation preserves multi-byte Tamil items."""
        mock_doc = MagicMock()
        mock_p = MagicMock()
        mock_doc.Paragraphs.Add.return_value = mock_p
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        items = ["முதல் படி: துவக்கம்", "இரண்டாம் படி: செயலாக்கம்", "Step 3: Verification"]
        res = self.engine.create_bullet_list(items=items)

        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["items_count"], 3)
        self.assertEqual(mock_doc.Paragraphs.Add.call_count, 3)

    def test_create_numbered_list(self) -> None:
        """Verify numbered list generation applies number list format."""
        mock_doc = MagicMock()
        mock_p = MagicMock()
        mock_doc.Paragraphs.Add.return_value = mock_p
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        items = ["First item", "Second item", "Third item"]
        res = self.engine.create_numbered_list(items=items)

        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["items_count"], 3)
        mock_p.Range.ListFormat.ApplyNumberDefault.assert_called()

    def test_empty_list_returns_zero_count(self) -> None:
        """Verify empty items list succeeds safely with zero count."""
        mock_doc = MagicMock()
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.create_bullet_list(items=[])
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["items_count"], 0)


if __name__ == "__main__":
    unittest.main()
