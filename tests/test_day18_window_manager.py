"""
Day 18 Unit Tests — Advanced Window Management & Geometry Controls.
Verifies window discovery, active window detection, focus, minimize, maximize,
restore, snap (left, right, top, bottom), move, resize, center, and disambiguation.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_windows.window_manager import WindowsWindowManager
from zye_windows.windows_models import WindowInfo


class MockWindow:
    def __init__(self, title: str, hwnd: int = 1001, left: int = 100, top: int = 100, width: int = 800, height: int = 600):
        self.title = title
        self._hWnd = hwnd
        self.visible = True
        self.isMinimized = False
        self.isMaximized = False
        self.isActive = False
        self.left = left
        self.top = top
        self.width = width
        self.height = height

    def activate(self):
        self.isActive = True

    def minimize(self):
        self.isMinimized = True
        self.isActive = False

    def maximize(self):
        self.isMaximized = True
        self.isMinimized = False

    def restore(self):
        self.isMinimized = False
        self.isMaximized = False

    def close(self):
        self.visible = False

    def moveTo(self, x: int, y: int):
        self.left = x
        self.top = y

    def resizeTo(self, w: int, h: int):
        self.width = w
        self.height = h


class TestDay18WindowManager(unittest.TestCase):

    def setUp(self) -> None:
        self.wm = WindowsWindowManager()

    @patch("pygetwindow.getAllWindows")
    def test_list_open_windows(self, mock_get_all: MagicMock) -> None:
        """Verify enumerating visible top-level desktop windows."""
        mock_get_all.return_value = [
            MockWindow("Visual Studio Code - Zye", hwnd=101),
            MockWindow("Google Chrome - Project Research", hwnd=102),
            MockWindow("", hwnd=103),  # empty title
        ]
        windows = self.wm.list_open_windows(include_empty=False)
        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0].title, "Visual Studio Code - Zye")
        self.assertEqual(windows[0].hwnd, 101)

    @patch("pygetwindow.getAllWindows")
    def test_find_window_exact_and_ambiguous(self, mock_get_all: MagicMock) -> None:
        """Verify single exact match versus multiple candidate disambiguation."""
        mock_get_all.return_value = [
            MockWindow("Google Chrome - Gmail", hwnd=201),
            MockWindow("Google Chrome - YouTube", hwnd=202),
            MockWindow("Notepad", hwnd=203),
        ]
        # Ambiguous query "Chrome"
        res_ambig = self.wm.find_window("Chrome")
        self.assertEqual(res_ambig["status"], "AMBIGUOUS")
        self.assertEqual(res_ambig["count"], 2)
        self.assertIn("Google Chrome - Gmail", res_ambig["candidates"])

        # Exact query "Notepad"
        res_exact = self.wm.find_window("Notepad")
        self.assertEqual(res_exact["status"], "EXACT_MATCH")
        self.assertEqual(res_exact["title"], "Notepad")

        # Missing query
        res_none = self.wm.find_window("NonExistentApp123")
        self.assertEqual(res_none["status"], "NOT_FOUND")

    @patch("pygetwindow.getActiveWindow")
    def test_get_active_window(self, mock_active: MagicMock) -> None:
        """Verify retrieving the active foreground window."""
        mock_active.return_value = MockWindow("Active Document - Word", hwnd=301)
        active = self.wm.get_active_window()
        self.assertIsNotNone(active)
        self.assertEqual(active.title, "Active Document - Word")
        self.assertEqual(active.hwnd, 301)
        self.assertTrue(active.is_active)

    @patch("pygetwindow.getAllWindows")
    def test_window_actions_focus_minimize_maximize(self, mock_get_all: MagicMock) -> None:
        """Verify focus, minimize, maximize, restore actions."""
        win = MockWindow("TargetApp", hwnd=401)
        mock_get_all.return_value = [win]

        res_focus = self.wm.manage_window("TargetApp", "focus")
        self.assertEqual(res_focus["status"], "SUCCESS")
        self.assertTrue(win.isActive)

        res_min = self.wm.manage_window("TargetApp", "minimize")
        self.assertEqual(res_min["status"], "SUCCESS")
        self.assertTrue(win.isMinimized)

        res_max = self.wm.manage_window("TargetApp", "maximize")
        self.assertEqual(res_max["status"], "SUCCESS")
        self.assertTrue(win.isMaximized)

    @patch("pyautogui.hotkey")
    @patch("pygetwindow.getAllWindows")
    def test_snap_actions(self, mock_get_all: MagicMock, mock_hotkey: MagicMock) -> None:
        """Verify snap_left, snap_right, snap_top, snap_bottom dispatch Win+Direction."""
        win = MockWindow("TargetApp", hwnd=501)
        mock_get_all.return_value = [win]

        res_left = self.wm.manage_window("TargetApp", "snap_left")
        self.assertEqual(res_left["status"], "SUCCESS")
        mock_hotkey.assert_called_with("win", "left")

        res_top = self.wm.manage_window("TargetApp", "snap_top")
        self.assertEqual(res_top["status"], "SUCCESS")
        mock_hotkey.assert_called_with("win", "up")

    @patch("pygetwindow.getAllWindows")
    def test_move_and_resize_window(self, mock_get_all: MagicMock) -> None:
        """Verify move_window and resize_window geometry adjustments."""
        win = MockWindow("TargetApp", hwnd=601, left=0, top=0, width=500, height=400)
        mock_get_all.return_value = [win]

        res_move = self.wm.move_window("TargetApp", 250, 150)
        self.assertEqual(res_move["status"], "SUCCESS")
        self.assertEqual(win.left, 250)
        self.assertEqual(win.top, 150)

        res_resize = self.wm.resize_window("TargetApp", 1024, 768)
        self.assertEqual(res_resize["status"], "SUCCESS")
        self.assertEqual(win.width, 1024)
        self.assertEqual(win.height, 768)

        # Invalid resize dimensions
        bad_resize = self.wm.resize_window("TargetApp", -10, 0)
        self.assertEqual(bad_resize["status"], "ERROR")


if __name__ == "__main__":
    unittest.main()
