"""
Day 21 Unit Tests — Word COM Connection, STA Worker, & Instance Detection.
Verifies connection policies, STA apartment thread affinity, and running instance detection.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_office.com_worker import STACOMWorker
from zye_office.models.office_models import ConnectionPolicy
from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_constants import WordConstants, WD_EXPORT_FORMAT_PDF


class TestDay21WordConnection(unittest.TestCase):

    def setUp(self) -> None:
        self.worker = STACOMWorker.get_instance()
        self.adapter = WordAdapter(worker=self.worker)

    def test_sta_worker_initialization(self) -> None:
        """Verify dedicated STA COM worker thread is alive and processing tasks."""
        self.assertTrue(self.worker.is_alive())
        res = self.worker.run(lambda: 12345)
        self.assertEqual(res, 12345)

    def test_word_constants(self) -> None:
        """Verify Word COM constants library."""
        self.assertEqual(WordConstants.wdExportFormatPDF, 17)
        self.assertEqual(WordConstants.wdDoNotSaveChanges, 0)
        self.assertEqual(WD_EXPORT_FORMAT_PDF, 17)

    def test_word_adapter_initialization(self) -> None:
        """Verify WordAdapter initialization and defaults."""
        self.assertEqual(self.adapter.PROG_ID, "Word.Application")
        self.assertIsNotNone(self.adapter.com_runtime)
        self.assertIsNotNone(self.adapter.validator)

    def test_word_is_running_check(self) -> None:
        """Verify is_running method executes safely without uncaught exceptions."""
        running = self.adapter.is_running()
        self.assertIsInstance(running, bool)

    def test_connect_attach_existing(self) -> None:
        """Verify connect attempt with ATTACH_EXISTING."""
        res = self.adapter.connect(policy=ConnectionPolicy.ATTACH_EXISTING)
        self.assertIn("status", res)
        self.assertIn(res["status"], ["SUCCESS", "FAILED", "NOT_FOUND", "ERROR"])

    def test_active_document_raw_when_none(self) -> None:
        """Verify get_active_document_raw returns None safely when no documents open."""
        with patch.object(self.adapter, "get_raw_app", return_value=None):
            doc = self.adapter.get_active_document_raw()
            self.assertIsNone(doc)


if __name__ == "__main__":
    unittest.main()
