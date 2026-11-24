"""
Unit Tests for Zye Day 20 Office Ribbon Accelerator.
Tests hotkey definitions, dangerous key filtering, and foreground window verification gates.
"""

import unittest
from unittest.mock import MagicMock, patch

from zye_office.ribbon_accelerator import OfficeRibbonAccelerator
from zye_office.models import OfficeAppType
from zye_office.errors import OfficeSecurityError, OfficeValidationError


class TestDay20RibbonAccelerator(unittest.TestCase):

    def setUp(self):
        self.accelerator = OfficeRibbonAccelerator()

    def test_predefined_action_hotkeys(self):
        self.assertIn("save", self.accelerator.ACTION_HOTKEYS)
        self.assertEqual(self.accelerator.ACTION_HOTKEYS["save"], ["ctrl", "s"])
        self.assertIn("bold", self.accelerator.ACTION_HOTKEYS)
        self.assertEqual(self.accelerator.ACTION_HOTKEYS["bold"], ["ctrl", "b"])

    def test_dangerous_keys_blocked(self):
        with self.assertRaises(OfficeSecurityError):
            self.accelerator.execute_accelerator(OfficeAppType.WORD, "alt+f4")

        with self.assertRaises(OfficeSecurityError):
            self.accelerator.execute_accelerator(OfficeAppType.WORD, "ctrl+alt+del")

    def test_empty_sequence_rejected(self):
        with self.assertRaises(OfficeValidationError):
            self.accelerator.execute_accelerator(OfficeAppType.WORD, "   ")

    @patch.object(OfficeRibbonAccelerator, "verify_foreground_app", return_value=False)
    @patch.object(OfficeRibbonAccelerator, "focus_app_window", return_value=False)
    def test_unfocused_window_raises_security_error(self, mock_focus, mock_verify):
        with self.assertRaises(OfficeSecurityError):
            self.accelerator.execute_accelerator(OfficeAppType.WORD, "save", auto_focus=True)


if __name__ == "__main__":
    unittest.main()
