"""
Day 21 Unit Tests — Word Document Manager.
Verifies document lifecycle operations, backup creation, metadata querying, and protection flags.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from zye_office.word.word_document_manager import WordDocumentManager
from zye_office.word.word_errors import WordNoActiveDocumentError, WordDocumentNotFoundError


class TestDay21DocumentManager(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_adapter = MagicMock()
        self.manager = WordDocumentManager(adapter=self.mock_adapter)

    def test_create_document_dispatches_to_adapter(self) -> None:
        """Verify create_document invokes adapter.create_document."""
        self.mock_adapter.create_document.return_value = {"status": "SUCCESS", "document_name": "Document1"}
        res = self.manager.create_document()
        self.assertEqual(res["status"], "SUCCESS")
        self.mock_adapter.create_document.assert_called_once()

    def test_open_document_dispatches_to_adapter(self) -> None:
        """Verify open_document passes file_path and read_only to adapter."""
        self.mock_adapter.open_document.return_value = {"status": "SUCCESS", "path": "C:\\test.docx"}
        res = self.manager.open_document("C:\\test.docx", read_only=True)
        self.assertEqual(res["status"], "SUCCESS")
        self.mock_adapter.open_document.assert_called_once_with("C:\\test.docx", read_only=True)

    def test_save_document_dispatches(self) -> None:
        """Verify save_document passes path."""
        self.mock_adapter.save_document.return_value = {"status": "SUCCESS"}
        res = self.manager.save_document(path="C:\\out.docx")
        self.assertEqual(res["status"], "SUCCESS")
        self.mock_adapter.save_document.assert_called_once_with(path="C:\\out.docx")

    def test_save_document_as_dispatches(self) -> None:
        """Verify save_document_as passes file_path."""
        self.mock_adapter.save_document_as.return_value = {"status": "SUCCESS"}
        res = self.manager.save_document_as("C:\\out2.docx")
        self.assertEqual(res["status"], "SUCCESS")
        self.mock_adapter.save_document_as.assert_called_once_with("C:\\out2.docx")

    def test_close_document_dispatches(self) -> None:
        """Verify close_document passes save_changes."""
        self.mock_adapter.close_document.return_value = {"status": "SUCCESS"}
        res = self.manager.close_document(save_changes=False)
        self.assertEqual(res["status"], "SUCCESS")
        self.mock_adapter.close_document.assert_called_once_with(save_changes=False)

    def test_create_backup_file_creation(self) -> None:
        """Verify document backup creates a timestamped file copy."""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(b"PK\x03\x04test content")
            src_path = f.name

        try:
            self.mock_adapter.get_active_document_raw.return_value = MagicMock(FullName=src_path)
            res = self.manager.create_document_backup(source_path=src_path)
            self.assertEqual(res["status"], "SUCCESS")
            backup_path = res["backup_path"]
            self.assertTrue(os.path.exists(backup_path))
            if os.path.exists(backup_path):
                os.remove(backup_path)
        finally:
            if os.path.exists(src_path):
                os.remove(src_path)

    def test_create_backup_nonexistent_file(self) -> None:
        """Verify error raised on non-existent document backup request."""
        with self.assertRaises(WordDocumentNotFoundError):
            self.manager.create_document_backup(source_path="C:\\nonexistent_dummy_99999.docx")


if __name__ == "__main__":
    unittest.main()
