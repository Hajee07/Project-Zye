"""
Day 21 Unit Tests — Word Style Manager & Corporate Presets.
Verifies built-in style queries, named style application, and corporate style presets.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_office.word.word_errors import WordNoActiveDocumentError, WordStyleNotFoundError
from zye_office.word.word_style_manager import STYLE_PRESETS, WordStyleManager


class TestDay21Styles(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_adapter = MagicMock()
        self.mock_adapter.worker.run.side_effect = lambda fn: fn()
        self.manager = WordStyleManager(adapter=self.mock_adapter)

    def test_list_corporate_presets(self) -> None:
        """Verify the 4 standard enterprise document presets exist."""
        presets = self.manager.list_corporate_presets()
        self.assertIn("BUSINESS_REPORT", presets)
        self.assertIn("ACADEMIC_REPORT", presets)
        self.assertIn("TECHNICAL_DOCUMENTATION", presets)
        self.assertIn("EXECUTIVE_SUMMARY", presets)

    def test_apply_word_style_success(self) -> None:
        """Verify applying built-in style to current selection."""
        mock_doc = MagicMock()
        mock_app = MagicMock()
        self.mock_adapter.get_raw_app.return_value = mock_app
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.manager.apply_word_style("Heading 1")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["style_name"], "Heading 1")
        self.assertEqual(mock_app.Selection.Range.Style, "Heading 1")

    def test_apply_style_preset(self) -> None:
        """Verify applying corporate preset configures styles."""
        mock_doc = MagicMock()
        mock_style = MagicMock()
        mock_doc.Styles.return_value = mock_style
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.manager.apply_style_preset("BUSINESS_REPORT")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["preset_name"], "BUSINESS_REPORT")

    def test_apply_invalid_preset_raises_error(self) -> None:
        """Verify unknown preset names raise WordStyleNotFoundError."""
        with self.assertRaises(WordStyleNotFoundError):
            self.manager.apply_style_preset("NON_EXISTENT_PRESET_XYZ")


if __name__ == "__main__":
    unittest.main()
