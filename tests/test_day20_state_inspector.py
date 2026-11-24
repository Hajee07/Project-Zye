"""
Unit Tests for Zye Day 20 Office State Inspector.
Tests active document inspection schemas and fallback handling for Word, Excel, PowerPoint, Outlook.
"""

import unittest
from unittest.mock import MagicMock

from zye_office.state_inspector import OfficeStateInspector
from zye_office.models import (
    WordDocumentMetadata,
    ExcelWorkbookMetadata,
    PowerPointPresentationMetadata,
    OutlookSessionMetadata,
)


class TestDay20StateInspector(unittest.TestCase):

    def setUp(self):
        self.inspector = OfficeStateInspector()

    def test_word_offline_inspection(self):
        # When Word is not running, inspector should return clean structured status
        res = self.inspector.inspect_active_word_document()
        self.assertIn("status", res)
        if res.get("status") == "SUCCESS":
            self.assertIn("word_count", res)
        else:
            self.assertIn("error_code", res)

    def test_excel_offline_inspection(self):
        res = self.inspector.inspect_active_excel_workbook()
        self.assertIn("status", res)

    def test_powerpoint_offline_inspection(self):
        res = self.inspector.inspect_active_powerpoint_presentation()
        self.assertIn("status", res)

    def test_outlook_offline_inspection(self):
        res = self.inspector.inspect_active_outlook_session()
        self.assertIn("status", res)

    def test_unsupported_app_inspection(self):
        res = self.inspector.inspect_live_office_app("photoshop")
        self.assertEqual(res.get("status"), "ERROR")
        self.assertIn("UNSUPPORTED_OFFICE_APP", res.get("error_code", ""))


if __name__ == "__main__":
    unittest.main()
