"""
Unit Tests for Zye Day 20 Office File Exporter.
Tests native COM PDF export constants, session validation, overwrite gates, and verification.
"""

import unittest
from unittest.mock import MagicMock
import tempfile
import os

from zye_office.file_exporter import OfficeFileExporter
from zye_office.models import OfficeAppType, SessionStatus, OfficeSessionMetadata
from zye_office.errors import OfficeFileExportError, OfficeValidationError


class TestDay20FileExporter(unittest.TestCase):

    def setUp(self):
        self.mock_runtime = MagicMock()
        self.mock_session_mgr = MagicMock()
        self.exporter = OfficeFileExporter(
            runtime=self.mock_runtime,
            session_manager=self.mock_session_mgr,
        )

    def test_constants_defined(self):
        self.assertEqual(OfficeFileExporter.WD_EXPORT_FORMAT_PDF, 17)
        self.assertEqual(OfficeFileExporter.XL_TYPE_PDF, 0)
        self.assertEqual(OfficeFileExporter.PP_SAVE_AS_PDF, 32)

    def test_outlook_export_not_supported(self):
        session = OfficeSessionMetadata(
            session_id="sess_out_1",
            app_name="outlook",
            prog_id="Outlook.Application",
            session_status=SessionStatus.ACTIVE,
        )
        self.mock_session_mgr.get_session.return_value = session
        with self.assertRaises(OfficeValidationError):
            self.exporter.export_active_to_pdf("sess_out_1", "output.pdf")

    def test_overwrite_protection(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"existing content")
            temp_path = f.name

        try:
            session = OfficeSessionMetadata(
                session_id="sess_w_1",
                app_name="word",
                prog_id="Word.Application",
                session_status=SessionStatus.ACTIVE,
            )
            self.mock_session_mgr.get_session.return_value = session

            # Overwrite=False on existing file must raise OfficeFileExportError
            with self.assertRaises(OfficeFileExportError):
                self.exporter.export_active_to_pdf("sess_w_1", temp_path, overwrite=False)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
