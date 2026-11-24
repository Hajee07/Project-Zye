"""
Unit Tests for Zye Day 20 Office Operation Executor.
Tests parameter validation, session verification, and STA dispatch routing.
"""

import unittest
from unittest.mock import MagicMock

from zye_office.operation_executor import OfficeOperationExecutor
from zye_office.models import OfficeAppType, SessionStatus, OfficeSessionMetadata
from zye_office.errors import OfficeValidationError


class TestDay20OperationExecutor(unittest.TestCase):

    def setUp(self):
        self.mock_runtime = MagicMock()
        self.mock_session_mgr = MagicMock()
        self.executor = OfficeOperationExecutor(
            runtime=self.mock_runtime,
            session_manager=self.mock_session_mgr,
        )

    def test_invalid_session_raises(self):
        self.mock_session_mgr.get_session.return_value = None
        with self.assertRaises(OfficeValidationError):
            self.executor.execute("invalid_sess", "word.insert_text", {"text": "test"})

    def test_mismatched_app_type_raises(self):
        session = OfficeSessionMetadata(
            session_id="sess_excel_1",
            app_name="excel",
            prog_id="Excel.Application",
            session_status=SessionStatus.ACTIVE,
        )
        self.mock_session_mgr.get_session.return_value = session
        with self.assertRaises(OfficeValidationError):
            # Attempting to run word operation on excel session
            self.executor.execute("sess_excel_1", "word.insert_text", {"text": "hello"})

    def test_inactive_session_raises(self):
        session = OfficeSessionMetadata(
            session_id="sess_word_1",
            app_name="word",
            prog_id="Word.Application",
            session_status=SessionStatus.DISCONNECTED,
        )
        self.mock_session_mgr.get_session.return_value = session
        with self.assertRaises(OfficeValidationError):
            self.executor.execute("sess_word_1", "word.insert_text", {"text": "hello"})


if __name__ == "__main__":
    unittest.main()
