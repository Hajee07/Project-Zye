"""
Day 18 Unit Tests — Keyboard Shortcuts & Named Hotkey Registry.
Verifies validated shortcut registry, key name authorization, modifier length limits,
and thread-safe input lock serialization.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_windows.input_controller import (
    ALLOWED_KEYS,
    INPUT_LOCK,
    NAMED_SHORTCUTS,
    WindowsInputController,
    normalize_shortcut_name,
)


class TestDay18Hotkeys(unittest.TestCase):

    def setUp(self) -> None:
        self.ic = WindowsInputController()

    def test_shortcut_normalization(self) -> None:
        """Verify normalizer handles variations in casing, spacing, and dashes."""
        self.assertEqual(normalize_shortcut_name("Alt + Tab"), "alt_tab")
        self.assertEqual(normalize_shortcut_name("ctrl-c"), "ctrl_c")
        self.assertEqual(normalize_shortcut_name("WIN + D"), "win_d")
        self.assertEqual(normalize_shortcut_name("ctrl + shift + esc"), "ctrl_shift_esc")

    def test_named_shortcut_registry_coverage(self) -> None:
        """Verify all mandatory shortcuts exist in the validated registry."""
        required = [
            "alt_tab", "win_tab", "win_d", "win_e", "win_i", "win_left", "win_right",
            "ctrl_c", "ctrl_v", "ctrl_x", "ctrl_a", "ctrl_z", "ctrl_y", "ctrl_s", "ctrl_f",
            "ctrl_shift_esc", "alt_f4", "esc", "enter", "tab"
        ]
        for sc in required:
            self.assertIn(sc, NAMED_SHORTCUTS, f"Missing required shortcut: {sc}")
            for k in NAMED_SHORTCUTS[sc]:
                self.assertIn(k, ALLOWED_KEYS, f"Key '{k}' in shortcut '{sc}' not in ALLOWED_KEYS")

    @patch("pyautogui.hotkey")
    def test_execute_valid_shortcut(self, mock_hotkey: MagicMock) -> None:
        """Verify executing registered shortcuts calls pyautogui.hotkey."""
        res = self.ic.execute_shortcut("Alt + Tab")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["shortcut_name"], "alt_tab")
        mock_hotkey.assert_called_with("alt", "tab")

        res_ctrl_c = self.ic.execute_shortcut("ctrl_c")
        self.assertEqual(res_ctrl_c["status"], "SUCCESS")
        mock_hotkey.assert_called_with("ctrl", "c")

    def test_reject_unregistered_shortcut(self) -> None:
        """Verify arbitrary or unregistered shortcut names are rejected."""
        res = self.ic.execute_shortcut("ctrl_alt_delete_dangerous")
        self.assertEqual(res["status"], "REJECTED")
        self.assertIn("not in validated registry", res["message"])

    def test_reject_unauthorized_individual_keys(self) -> None:
        """Verify press_hotkey rejects unwhitelisted keys."""
        res = self.ic.press_hotkey(["ctrl", "malicious_injected_key"])
        self.assertEqual(res["status"], "REJECTED")

    def test_reject_excessive_combination_length(self) -> None:
        """Verify combinations longer than 4 keys are rejected for security."""
        res = self.ic.press_hotkey(["ctrl", "alt", "shift", "win", "a"])
        self.assertEqual(res["status"], "REJECTED")

    def test_input_lock_reentrancy(self) -> None:
        """Verify INPUT_LOCK can be acquired cleanly."""
        with INPUT_LOCK:
            # Re-entrant acquire
            with INPUT_LOCK:
                self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
