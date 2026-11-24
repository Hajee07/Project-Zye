"""
Day 21 Unit Tests — Word Metadata & Statistics Engine.
Verifies reading and writing built-in document properties (Title, Author, Subject, Keywords) and exact word statistics.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_office.word.word_errors import WordNoActiveDocumentError
from zye_office.word.word_metadata import WordMetadataEngine


class TestDay21Metadata(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_adapter = MagicMock()
        self.mock_adapter.worker.run.side_effect = lambda fn: fn()
        self.engine = WordMetadataEngine(adapter=self.mock_adapter)

    def test_get_document_statistics(self) -> None:
        """Verify computing document words, characters, pages, and paragraph counts."""
        mock_doc = MagicMock()
        mock_doc.ComputeStatistics.side_effect = lambda stat: {
            0: 120,   # wdStatisticWords
            3: 850,   # wdStatisticCharacters
            2: 3,     # wdStatisticPages
            4: 15,    # wdStatisticParagraphs
            1: 45,    # wdStatisticLines
        }.get(stat, 0)
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.get_document_statistics()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["words"], 120)
        self.assertEqual(res["characters"], 850)
        self.assertEqual(res["pages"], 3)
        self.assertEqual(res["paragraphs"], 15)

    def test_set_document_properties(self) -> None:
        """Verify setting built-in document properties."""
        mock_doc = MagicMock()
        mock_props = MagicMock()
        mock_item = MagicMock()
        mock_props.return_value = mock_item
        mock_doc.BuiltInDocumentProperties = mock_props
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.set_document_properties(
            title="Q4 Architecture Report",
            author="Zye AI Lead",
            subject="System Automation",
            keywords="AI, COM, Word, Python",
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["updated"]["title"], "Q4 Architecture Report")
        self.assertEqual(res["updated"]["author"], "Zye AI Lead")


if __name__ == "__main__":
    unittest.main()
