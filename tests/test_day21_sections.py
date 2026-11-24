"""
Day 21 Unit Tests — Word Section Manager.
Verifies multi-section queries, section break generation, and unlinking headers/footers from previous sections.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_office.word.word_errors import WordNoActiveDocumentError
from zye_office.word.word_section_manager import WordSectionManager


class TestDay21Sections(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_adapter = MagicMock()
        self.mock_adapter.worker.run.side_effect = lambda fn: fn()
        self.manager = WordSectionManager(adapter=self.mock_adapter)

    def test_get_document_sections(self) -> None:
        """Verify querying section list and properties."""
        mock_doc = MagicMock()
        mock_doc.Sections.Count = 2
        mock_sec1 = MagicMock()
        mock_sec1.PageSetup.Orientation = 0  # Portrait
        mock_sec2 = MagicMock()
        mock_sec2.PageSetup.Orientation = 1  # Landscape
        mock_doc.Sections.side_effect = lambda idx: mock_sec1 if idx == 1 else mock_sec2
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.manager.get_document_sections()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["total_sections"], 2)
        self.assertEqual(res["sections"][0]["orientation"], "PORTRAIT")
        self.assertEqual(res["sections"][1]["orientation"], "LANDSCAPE")

    def test_create_document_section(self) -> None:
        """Verify inserting section break."""
        mock_doc = MagicMock()
        mock_app = MagicMock()
        mock_doc.Sections.Count = 3
        self.mock_adapter.get_raw_app.return_value = mock_app
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.manager.create_document_section()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["new_total_sections"], 3)
        mock_app.Selection.InsertBreak.assert_called_once()

    def test_unlink_header_from_previous(self) -> None:
        """Verify unlinking LinkToPrevious on section 2."""
        mock_doc = MagicMock()
        mock_doc.Sections.Count = 3
        mock_sec = MagicMock()
        mock_doc.Sections.return_value = mock_sec
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.manager.unlink_header_from_previous(section_index=2)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertFalse(mock_sec.Headers(1).LinkToPrevious)
        self.assertFalse(mock_sec.Footers(1).LinkToPrevious)


if __name__ == "__main__":
    unittest.main()
