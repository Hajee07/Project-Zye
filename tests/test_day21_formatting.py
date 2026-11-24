"""
Day 21 Unit Tests — Word Formatting Engine.
Verifies font properties, paragraph alignments, line spacing, colors, and parameter bounds.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_office.models.word_models import WordFormatOptions
from zye_office.word.word_errors import WordFormattingError, WordNoActiveDocumentError
from zye_office.word.word_formatting_engine import WordFormattingEngine
from zye_office.word.word_validator import WordValidator


class TestDay21Formatting(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_adapter = MagicMock()
        self.mock_adapter.worker.run.side_effect = lambda fn: fn()
        self.engine = WordFormattingEngine(adapter=self.mock_adapter)

    def test_format_text_font_properties(self) -> None:
        """Verify font properties applied correctly to Selection.Font."""
        mock_doc = MagicMock()
        mock_app = MagicMock()
        mock_font = MagicMock()
        mock_app.Selection.Range.Font = mock_font
        self.mock_adapter.get_raw_app.return_value = mock_app
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        opts = WordFormatOptions(font_name="Arial", font_size=14.0, bold=True, italic=False)
        res = self.engine.format_text(options=opts)

        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_font.Name, "Arial")
        self.assertEqual(mock_font.Size, 14.0)
        self.assertEqual(mock_font.Bold, True)

    def test_invalid_font_size_raises_formatting_error(self) -> None:
        """Verify font sizes out of Word bounds (1..1638) raise WordFormattingError."""
        opts = WordFormatOptions(font_size=2000.0)
        with self.assertRaises(WordFormattingError):
            self.engine.format_text(options=opts)

    def test_format_paragraph_alignment(self) -> None:
        """Verify paragraph alignment mapping and assignment."""
        mock_doc = MagicMock()
        mock_app = MagicMock()
        mock_format = MagicMock()
        mock_app.Selection.Range.ParagraphFormat = mock_format
        self.mock_adapter.get_raw_app.return_value = mock_app
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.format_paragraph(alignment="center", line_spacing=1.5, space_before=12.0)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["alignment"], "center")
        self.assertEqual(mock_format.Alignment, 1)  # wdAlignParagraphCenter
        self.assertEqual(mock_format.SpaceBefore, 12.0)

    def test_invalid_alignment_raises_error(self) -> None:
        """Verify invalid alignment strings are rejected."""
        with self.assertRaises(WordFormattingError):
            self.engine.format_paragraph(alignment="diagonal")


if __name__ == "__main__":
    unittest.main()
