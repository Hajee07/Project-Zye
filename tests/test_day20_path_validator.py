"""
Unit Tests for Zye Day 20 Office Path Validator.
Tests canonical resolution, path traversal defense, and allowed Office/PDF extensions.
"""

import unittest
import os
import pathlib
import tempfile

from zye_office.path_validator import OfficePathValidator, ALLOWED_OFFICE_EXTENSIONS
from zye_office.errors import OfficeSecurityError, OfficeValidationError


class TestDay20PathValidator(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = pathlib.Path(self.temp_dir.name)
        self.validator = OfficePathValidator(workspace_root=self.workspace)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_valid_word_path(self):
        valid_path = str(self.workspace / "document.docx")
        canon = self.validator.validate_path(valid_path)
        self.assertTrue(canon.endswith("document.docx"))

    def test_valid_pdf_path(self):
        valid_pdf = str(self.workspace / "exports" / "report.pdf")
        canon = self.validator.validate_path(valid_pdf)
        self.assertTrue(canon.endswith("report.pdf"))

    def test_traversal_detection_raises_security_error(self):
        traversal_path = "../../windows/system32/cmd.exe"
        with self.assertRaises(OfficeSecurityError):
            self.validator.validate_path(traversal_path)

    def test_unauthorized_extension_raises_validation_error(self):
        malicious_ext = str(self.workspace / "script.bat")
        with self.assertRaises(OfficeValidationError):
            self.validator.validate_path(malicious_ext)

    def test_empty_path_raises_validation_error(self):
        with self.assertRaises(OfficeValidationError):
            self.validator.validate_path("")

    def test_allowed_extensions_set(self):
        self.assertIn(".docx", ALLOWED_OFFICE_EXTENSIONS)
        self.assertIn(".xlsx", ALLOWED_OFFICE_EXTENSIONS)
        self.assertIn(".pptx", ALLOWED_OFFICE_EXTENSIONS)
        self.assertIn(".pdf", ALLOWED_OFFICE_EXTENSIONS)


if __name__ == "__main__":
    unittest.main()
