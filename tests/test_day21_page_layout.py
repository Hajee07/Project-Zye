"""
Day 21 Unit Tests — Word Page Layout Engine.
Verifies page orientation (Portrait/Landscape), standard paper sizes (A4, Letter, Legal, A3), margins, and column layouts.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_office.word.word_errors import WordLayoutOperationError, WordNoActiveDocumentError
from zye_office.word.word_page_layout import WordPageLayoutEngine, WordPageLayoutManager


class TestDay21PageLayout(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_adapter = MagicMock()
        self.mock_adapter.worker.run.side_effect = lambda fn: fn()
        self.engine = WordPageLayoutManager(adapter=self.mock_adapter)

    def test_set_page_orientation_landscape(self) -> None:
        """Verify setting orientation to LANDSCAPE."""
        mock_doc = MagicMock()
        mock_setup = MagicMock()
        mock_doc.PageSetup = mock_setup
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.set_page_orientation("landscape")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["orientation"], "LANDSCAPE")
        self.assertEqual(mock_setup.Orientation, 1)  # wdOrientLandscape

    def test_set_paper_size_a4(self) -> None:
        """Verify setting paper size to A4."""
        mock_doc = MagicMock()
        mock_setup = MagicMock()
        mock_doc.PageSetup = mock_setup
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.set_paper_size("A4")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["paper_size"], "A4")
        self.assertEqual(mock_setup.PaperSize, 7)  # wdPaperA4

    def test_invalid_paper_size_raises_error(self) -> None:
        """Verify unknown paper size raises WordLayoutOperationError."""
        with self.assertRaises(WordLayoutOperationError):
            self.engine.set_paper_size("SUPER_A0_BANNER")

    def test_set_page_margins(self) -> None:
        """Verify setting margins in points."""
        mock_doc = MagicMock()
        mock_setup = MagicMock()
        mock_doc.PageSetup = mock_setup
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.set_page_margins(top=72.0, bottom=72.0, left=54.0, right=54.0)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_setup.TopMargin, 72.0)
        self.assertEqual(mock_setup.BottomMargin, 72.0)
        self.assertEqual(mock_setup.LeftMargin, 54.0)
        self.assertEqual(mock_setup.RightMargin, 54.0)

    def test_set_page_columns(self) -> None:
        """Verify setting multi-column text layout."""
        mock_doc = MagicMock()
        mock_setup = MagicMock()
        mock_doc.PageSetup = mock_setup
        mock_cols = MagicMock()
        mock_setup.TextColumns = mock_cols
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.set_page_columns(columns=2, spacing_pt=18.0)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["columns"], 2)
        mock_cols.SetCount.assert_called_once_with(2)


if __name__ == "__main__":
    unittest.main()
