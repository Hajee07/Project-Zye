"""
Unit Tests for Zye Day 20 Office Operation Registry.
Tests allowlisted typed operations, parameter validation, default values, and rejection of unverified operations.
"""

import unittest
from zye_office.operation_registry import OfficeOperationRegistry, OperationDef, ParamDef
from zye_office.models import OfficeAppType, RiskCategory
from zye_office.errors import OfficeSecurityError, OfficeValidationError


class TestDay20OperationRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = OfficeOperationRegistry()

    def test_registered_operations_count(self):
        ops = self.registry.list_operations()
        self.assertGreaterEqual(len(ops), 14)

    def test_word_operations_exist(self):
        op = self.registry.get_operation("word.insert_text")
        self.assertIsNotNone(op)
        self.assertEqual(op.app_type, OfficeAppType.WORD)
        self.assertEqual(op.risk_level, RiskCategory.LOW_RISK)

    def test_excel_operations_exist(self):
        op = self.registry.get_operation("excel.set_cell_value")
        self.assertIsNotNone(op)
        self.assertEqual(op.app_type, OfficeAppType.EXCEL)

    def test_validate_and_normalize_valid_params(self):
        op, clean = self.registry.validate_and_normalize(
            "word.insert_text",
            {"text": "Hello world", "location": "end"},
        )
        self.assertEqual(clean["text"], "Hello world")
        self.assertEqual(clean["location"], "end")

    def test_validate_missing_required_param_raises(self):
        with self.assertRaises(OfficeValidationError):
            self.registry.validate_and_normalize("word.insert_text", {})

    def test_unregistered_operation_raises_security_error(self):
        with self.assertRaises(OfficeSecurityError):
            self.registry.validate_and_normalize("malicious.execute_vba", {})

    def test_unknown_param_rejected(self):
        with self.assertRaises(OfficeValidationError):
            self.registry.validate_and_normalize(
                "word.insert_text",
                {"text": "Sample", "injection_key": "bad_data"},
            )


if __name__ == "__main__":
    unittest.main()
