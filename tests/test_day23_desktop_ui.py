"""
Day 23 Comprehensive Test Suite — Universal Desktop UI Automation & Ribbon Accelerators.
Tests Foreground Window Guard, UI Inspector, Bounded Keyboard Sequence Engine,
and Ribbon Menu Accelerators.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_office.desktop_ui.foreground_window_guard import ForegroundWindowGuard
from zye_office.desktop_ui.ui_inspector import DesktopUIInspector
from zye_office.desktop_ui.keyboard_sequence_engine import KeyboardSequenceEngine
from zye_office.desktop_ui.ribbon_accelerator import DesktopRibbonAccelerator
from zye_office.desktop_ui.ui_errors import (
    UIWindowNotFoundError,
    UIForegroundMismatchError,
)


class TestDay23DesktopUIAutomation(unittest.TestCase):

    def setUp(self) -> None:
        self.guard = ForegroundWindowGuard()
        self.inspector = DesktopUIInspector()
        self.keyboard_engine = KeyboardSequenceEngine()
        self.ribbon_accelerator = DesktopRibbonAccelerator(keyboard_engine=self.keyboard_engine)

    def test_foreground_guard_inspect_window(self) -> None:
        """Verify foreground window inspection executes safely or raises UIWindowNotFoundError when headless."""
        try:
            info = self.guard.get_foreground_window_info()
            self.assertIsInstance(info, dict)
            self.assertIn("hwnd", info)
            self.assertIn("title", info)
            self.assertIn("process_name", info)
        except UIWindowNotFoundError:
            # Expected in non-interactive/headless environments
            pass

    def test_keyboard_sequence_bounds(self) -> None:
        """Verify bounded keyboard sequence limits sequence length to prevent runaway automation."""
        excessive_keys = ["a"] * 25
        with self.assertRaises(ValueError):
            self.keyboard_engine.execute_sequence(excessive_keys)

    def test_ribbon_accelerator_trigger(self) -> None:
        """Verify ribbon accelerator constructs proper Alt sequence."""
        with patch.object(self.keyboard_engine, "execute_sequence", return_value={"status": "SUCCESS"}) as mock_exec:
            res = self.ribbon_accelerator.trigger_ribbon_tab("h", expected_process="WINWORD.EXE")
            self.assertEqual(res["status"], "SUCCESS")
            mock_exec.assert_called_once_with(["alt", "h"], expected_process="WINWORD.EXE")

    def test_guard_process_validation(self) -> None:
        """Verify verification against target process."""
        mock_win_info = {"process_name": "notepad.exe", "title": "Untitled - Notepad", "hwnd": 1234, "pid": 5678}
        with patch("zye_office.desktop_ui.foreground_window_guard.ForegroundWindowGuard.get_foreground_window_info", return_value=mock_win_info):
            self.assertTrue(self.guard.verify_foreground_process("notepad.exe"))
            with self.assertRaises(UIForegroundMismatchError):
                self.guard.verify_foreground_process("powerpnt.exe")


if __name__ == "__main__":
    unittest.main()
