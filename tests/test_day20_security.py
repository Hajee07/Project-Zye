"""
Unit Tests for Zye Day 20 Office Security & Zero-Trust Policies.
Tests prohibition of arbitrary exec/eval/VBA, path traversal blocking, and authorization.
"""

import unittest
from zye_office.operation_registry import OfficeOperationRegistry
from zye_office.path_validator import OfficePathValidator
from zye_office.ribbon_accelerator import OfficeRibbonAccelerator
from zye_office.models import OfficeAppType
from zye_office.errors import OfficeSecurityError


class TestDay20Security(unittest.TestCase):

    def setUp(self):
        self.op_registry = OfficeOperationRegistry()
        self.path_validator = OfficePathValidator()
        self.ribbon_accelerator = OfficeRibbonAccelerator()

    def test_arbitrary_code_execution_blocked(self):
        dangerous_ops = [
            "system.eval",
            "python.exec",
            "word.run_vba_macro",
            "excel.execute_script",
            "powershell.invoke",
        ]
        for op in dangerous_ops:
            with self.assertRaises(OfficeSecurityError):
                self.op_registry.validate_and_normalize(op, {})

    def test_path_traversal_blocked(self):
        attacks = [
            "../../etc/passwd",
            "..\\..\\windows\\system32\\calc.exe",
            "exports/../../../secret.txt",
        ]
        for attack in attacks:
            with self.assertRaises(OfficeSecurityError):
                self.path_validator.validate_path(attack)

    def test_dangerous_shortcuts_blocked(self):
        dangerous_keys = [
            "alt+f4",
            "ctrl+alt+del",
            "win",
        ]
        for dk in dangerous_keys:
            with self.assertRaises(OfficeSecurityError):
                self.ribbon_accelerator.execute_accelerator(OfficeAppType.WORD, dk)


if __name__ == "__main__":
    unittest.main()
