"""
Day 21 Unit Tests — Word Document Accessibility Engine.
Verifies compliance auditing for document title, heading hierarchy, table header rows, image alt texts, and link descriptions.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_office.word.word_accessibility import WordAccessibilityEngine
from zye_office.word.word_errors import WordNoActiveDocumentError


class TestDay21Accessibility(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_adapter = MagicMock()
        self.mock_adapter.worker.run.side_effect = lambda fn: fn()
        self.engine = WordAccessibilityEngine(adapter=self.mock_adapter)

    def test_audit_accessible_document(self) -> None:
        """Verify compliance score 100 on document with title, valid headings, and table headers."""
        mock_doc = MagicMock()
        mock_title_prop = MagicMock(Value="Comprehensive Architecture Plan")
        mock_doc.BuiltInDocumentProperties.return_value = mock_title_prop

        # Heading 1 present
        mock_p = MagicMock()
        mock_p.Range.Style.NameLocal = "Heading 1"
        mock_p.Style.NameLocal = "Heading 1"
        mock_p.Range.Text = "Section One\r"
        mock_doc.Paragraphs = [mock_p]

        # Table with header row
        mock_tbl = MagicMock()
        mock_tbl.Rows(1).HeadingFormat = -1  # True in COM
        mock_doc.Tables = [mock_tbl]

        # Inline shape with alt text
        mock_shape = MagicMock()
        mock_shape.AlternativeText = "Detailed system architecture diagram"
        mock_doc.InlineShapes = [mock_shape]

        mock_doc.Hyperlinks = []
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.inspect_document_accessibility()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["compliance_score"], 100)
        self.assertTrue(res["passed"])
        self.assertEqual(len(res["issues"]), 0)

    def test_audit_inaccessible_document_detects_issues(self) -> None:
        """Verify issues detected when title is missing and table lacks header row."""
        mock_doc = MagicMock()
        mock_title_prop = MagicMock(Value="")
        mock_doc.BuiltInDocumentProperties.return_value = mock_title_prop

        mock_doc.Paragraphs = []
        mock_tbl = MagicMock()
        mock_tbl.Rows(1).HeadingFormat = 0  # Missing header
        mock_doc.Tables = [mock_tbl]
        mock_doc.InlineShapes = []
        mock_doc.Hyperlinks = []
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.inspect_document_accessibility()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertLess(res["compliance_score"], 100)
        self.assertFalse(res["passed"])
        self.assertGreater(len(res["issues"]), 0)


if __name__ == "__main__":
    unittest.main()
