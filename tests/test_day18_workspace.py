"""
Day 18 Unit Tests — Windows Virtual Desktop Management.
Verifies virtual desktop discovery, desktop creation, switching, and closing.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_windows.workspace_manager import WindowsWorkspaceManager


class TestDay18Workspace(unittest.TestCase):

    def setUp(self) -> None:
        self.wsm = WindowsWorkspaceManager()

    def test_get_virtual_desktops_initial(self) -> None:
        """Verify initial virtual desktop query returns at least 1 desktop."""
        res = self.wsm.get_virtual_desktops()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["count"], 1)
        self.assertEqual(len(res["desktops"]), 1)
        self.assertTrue(res["desktops"][0]["is_current"])

    @patch("pyautogui.hotkey")
    def test_create_virtual_desktop(self, mock_hotkey: MagicMock) -> None:
        """Verify creating a new virtual desktop increments count and dispatches Win+Ctrl+D."""
        res = self.wsm.create_virtual_desktop()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["new_count"], 2)
        self.assertEqual(res["current_index"], 1)
        mock_hotkey.assert_called_with("win", "ctrl", "d")

    @patch("pyautogui.hotkey")
    def test_switch_virtual_desktop(self, mock_hotkey: MagicMock) -> None:
        """Verify switching desktops (next, previous, index)."""
        # Create a second desktop first
        self.wsm.create_virtual_desktop()
        self.assertEqual(self.wsm._current_index, 1)

        # Switch to previous
        res_prev = self.wsm.switch_virtual_desktop("previous")
        self.assertEqual(res_prev["status"], "SUCCESS")
        self.assertEqual(res_prev["current_index"], 0)
        mock_hotkey.assert_called_with("win", "ctrl", "left")

        # Switch to next
        res_next = self.wsm.switch_virtual_desktop("next")
        self.assertEqual(res_next["status"], "SUCCESS")
        self.assertEqual(res_next["current_index"], 1)
        mock_hotkey.assert_called_with("win", "ctrl", "right")

    @patch("pyautogui.hotkey")
    def test_close_virtual_desktop(self, mock_hotkey: MagicMock) -> None:
        """Verify closing a virtual desktop dispatches Win+Ctrl+F4."""
        self.wsm._desktop_count = 2
        self.wsm._current_index = 1

        res = self.wsm.close_virtual_desktop()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["remaining_count"], 1)
        mock_hotkey.assert_called_with("win", "ctrl", "f4")

        # Closing when only 1 desktop remains should be blocked
        res_blocked = self.wsm.close_virtual_desktop()
        self.assertEqual(res_blocked["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
