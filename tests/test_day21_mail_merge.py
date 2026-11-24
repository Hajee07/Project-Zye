"""
Day 21 Unit Tests — Word Mail Merge Engine.
Verifies data source validation (CSV/Excel headers & records), connecting mail merge source, and merge execution.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock

from zye_office.word.word_errors import WordMailMergeError, WordNoActiveDocumentError
from zye_office.word.word_mail_merge import WordMailMergeEngine


class TestDay21MailMerge(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_adapter = MagicMock()
        self.mock_adapter.worker.run.side_effect = lambda fn: fn()
        self.engine = WordMailMergeEngine(adapter=self.mock_adapter)

    def test_validate_csv_data_source(self) -> None:
        """Verify reading CSV headers and counting records."""
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False, encoding="utf-8") as f:
            f.write("FullName,Email,Company\nAlice,alice@example.com,Zye Corp\nBob,bob@example.com,Acme\n")
            csv_path = f.name

        try:
            res = self.engine.validate_data_source(csv_path)
            self.assertEqual(res["status"], "SUCCESS")
            self.assertEqual(res["headers"], ["FullName", "Email", "Company"])
            self.assertEqual(res["total_records"], 2)
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)

    def test_connect_mail_merge_source(self) -> None:
        """Verify calling OpenDataSource on Word MailMerge."""
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False, encoding="utf-8") as f:
            f.write("ID,Name\n1,Alpha\n")
            csv_path = f.name

        try:
            mock_doc = MagicMock()
            mock_mm = MagicMock()
            mock_doc.MailMerge = mock_mm
            self.mock_adapter.get_active_document_raw.return_value = mock_doc

            res = self.engine.connect_mail_merge_source(csv_path)
            self.assertEqual(res["status"], "SUCCESS")
            mock_mm.OpenDataSource.assert_called_once()
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)

    def test_execute_mail_merge(self) -> None:
        """Verify executing mail merge to a new document."""
        mock_doc = MagicMock()
        mock_mm = MagicMock()
        mock_doc.MailMerge = mock_mm
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.execute_mail_merge()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["destination"], "NEW_DOCUMENT")
        mock_mm.Execute.assert_called_once_with(Pause=False)


if __name__ == "__main__":
    unittest.main()
