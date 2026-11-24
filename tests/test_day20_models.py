"""
Unit Tests for Zye Day 20 Office Data Models.
Tests Pydantic schemas, enums, serialization, and default values.
"""

import unittest
from zye_office.models import (
    OfficeAppType,
    ConnectionPolicy,
    SessionStatus,
    RiskCategory,
    OfficeAppInfo,
    OfficeSessionMetadata,
    WordDocumentMetadata,
    ExcelWorkbookMetadata,
    PowerPointPresentationMetadata,
    OutlookSessionMetadata,
    PDFExportResult,
)


class TestDay20Models(unittest.TestCase):

    def test_office_app_type_enum(self):
        self.assertEqual(OfficeAppType.WORD.value, "word")
        self.assertEqual(OfficeAppType.EXCEL.value, "excel")
        self.assertEqual(OfficeAppType.POWERPOINT.value, "powerpoint")
        self.assertEqual(OfficeAppType.OUTLOOK.value, "outlook")

    def test_connection_policy_enum(self):
        self.assertEqual(ConnectionPolicy.ATTACH_EXISTING.value, "ATTACH_EXISTING")
        self.assertEqual(ConnectionPolicy.LAUNCH_NEW.value, "LAUNCH_NEW")

    def test_session_metadata_serialization(self):
        meta = OfficeSessionMetadata(
            session_id="sess_test_123",
            app_name="word",
            prog_id="Word.Application",
        )
        d = meta.model_dump()
        self.assertEqual(d["session_id"], "sess_test_123")
        self.assertEqual(d["app_name"], "word")
        self.assertTrue(meta.is_active)
        self.assertEqual(meta.app_type, OfficeAppType.WORD)

    def test_word_metadata_model(self):
        doc = WordDocumentMetadata(word_count=500, page_count=3)
        self.assertEqual(doc.word_count, 500)
        self.assertEqual(doc.page_count, 3)
        self.assertEqual(doc.app_name, "word")

    def test_excel_metadata_model(self):
        wb = ExcelWorkbookMetadata(active_sheet_name="Summary")
        self.assertEqual(wb.active_sheet_name, "Summary")
        self.assertEqual(wb.app_name, "excel")

    def test_powerpoint_metadata_model(self):
        pres = PowerPointPresentationMetadata(slide_count=10)
        self.assertEqual(pres.slide_count, 10)
        self.assertEqual(pres.app_name, "powerpoint")

    def test_pdf_export_result_model(self):
        res = PDFExportResult(
            success=True,
            source_app=OfficeAppType.WORD,
            output_path="C:/temp/doc.pdf",
            file_size_bytes=1024,
            pages_exported=2,
            elapsed_ms=120.5,
        )
        self.assertTrue(res.success)
        self.assertEqual(res.file_size_bytes, 1024)


if __name__ == "__main__":
    unittest.main()
