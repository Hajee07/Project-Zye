"""
Day 21 Unit Tests — Word Headers and Footers Manager.
Verifies header and footer text injection, alignments, different first page, and dynamic page numbering.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_office.word.word_errors import WordNoActiveDocumentError
from zye_office.word.word_header_footer import WordHeaderFooterEngine, WordHeaderFooterManager


class TestDay21HeadersFooters(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_adapter = MagicMock()
        self.mock_adapter.worker.run.side_effect = lambda fn: fn()
        self.engine = WordHeaderFooterManager(adapter=self.mock_adapter)

    def test_set_header_text(self) -> None:
        """Verify setting header text on section 1."""
        mock_doc = MagicMock()
        mock_sec = MagicMock()
        mock_hdr = MagicMock()
        mock_sec.Headers.return_value = mock_hdr
        mock_doc.Sections.return_value = mock_sec
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.set_header("Zye AI Confidential Report", section_index=1, alignment="right")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_hdr.Range.Text, "Zye AI Confidential Report")

    def test_set_footer_text(self) -> None:
        """Verify setting footer text on section 1."""
        mock_doc = MagicMock()
        mock_sec = MagicMock()
        mock_ftr = MagicMock()
        mock_sec.Footers.return_value = mock_ftr
        mock_doc.Sections.return_value = mock_sec
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.set_footer("Page Copyright 2026", section_index=1, alignment="center")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(mock_ftr.Range.Text, "Page Copyright 2026")

    def test_different_first_page_toggle(self) -> None:
        """Verify DifferentFirstPageHeaderFooter toggle."""
        mock_doc = MagicMock()
        mock_sec = MagicMock()
        mock_doc.Sections.return_value = mock_sec
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.set_different_first_page(enabled=True, section_index=1)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(mock_sec.PageSetup.DifferentFirstPageHeaderFooter)

    def test_insert_page_numbers(self) -> None:
        """Verify dynamic PAGE field insertion into footer."""
        mock_doc = MagicMock()
        mock_sec = MagicMock()
        mock_ftr = MagicMock()
        mock_sec.Footers.return_value = mock_ftr
        mock_doc.Sections.return_value = mock_sec
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.insert_page_numbers(position="footer_right", section_index=1)
        self.assertEqual(res["status"], "SUCCESS")
        mock_doc.Fields.Add.assert_called_once()


if __name__ == "__main__":
    unittest.main()
