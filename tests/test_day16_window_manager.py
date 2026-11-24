"""Day 16 Unit Tests — Universal Window Management Engine."""
import unittest
from unittest.mock import MagicMock, patch

from zye_windows.window_manager import WindowsWindowManager


class TestWindowsWindowManager(unittest.TestCase):
    def setUp(self):
        self.wm = WindowsWindowManager()

    def test_unsupported_action(self):
        res = self.wm.manage_window("notepad", "spin_around")
        self.assertEqual(res["status"], "ERROR")
        self.assertIn("Unsupported action", res["message"])

    @patch("zye_windows.window_manager.gw")
    def test_list_windows(self, mock_gw):
        w1 = MagicMock()
        w1.title = "Visual Studio Code"
        w1._hWnd = 101
        w1.visible = True
        w1.isMinimized = False
        w1.isMaximized = True
        w1.isActive = True
        w1.left = 0
        w1.top = 0
        w1.width = 1920
        w1.height = 1080

        w2 = MagicMock()
        w2.title = ""
        mock_gw.getAllWindows.return_value = [w1, w2]

        windows = self.wm.list_windows()
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0].title, "Visual Studio Code")

    @patch.object(WindowsWindowManager, "find_windows")
    def test_window_not_found(self, mock_find):
        mock_find.return_value = []
        res = self.wm.manage_window("Calculator", "focus")
        self.assertEqual(res["status"], "WINDOW_NOT_FOUND")

    @patch.object(WindowsWindowManager, "find_windows")
    def test_ambiguous_window(self, mock_find):
        w1 = MagicMock()
        w1.title = "Chrome - Tab 1"
        w2 = MagicMock()
        w2.title = "Chrome - Tab 2"
        mock_find.return_value = [w1, w2]

        res = self.wm.manage_window("Chrome", "focus")
        self.assertEqual(res["status"], "AMBIGUOUS_WINDOW")
        self.assertEqual(len(res["candidates"]), 2)

    @patch.object(WindowsWindowManager, "find_windows")
    def test_focus_window(self, mock_find):
        target = MagicMock()
        target.title = "WhatsApp"
        mock_find.return_value = [target]

        res = self.wm.manage_window("WhatsApp", "focus")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["action"], "focus")
        target.activate.assert_called_once()

    @patch.object(WindowsWindowManager, "find_windows")
    def test_minimize_window(self, mock_find):
        target = MagicMock()
        target.title = "WhatsApp"
        mock_find.return_value = [target]

        res = self.wm.manage_window("WhatsApp", "minimize")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["action"], "minimize")
        target.minimize.assert_called_once()

    @patch.object(WindowsWindowManager, "find_windows")
    def test_snap_left_window(self, mock_find):
        target = MagicMock()
        target.title = "Chrome"
        mock_find.return_value = [target]

        with patch("pyautogui.hotkey") as mock_hotkey:
            res = self.wm.manage_window("Chrome", "snap_left")
            self.assertEqual(res["status"], "SUCCESS")
            mock_hotkey.assert_called_with("win", "left")

    @patch.object(WindowsWindowManager, "find_windows")
    def test_snap_right_window(self, mock_find):
        target = MagicMock()
        target.title = "Chrome"
        mock_find.return_value = [target]

        with patch("pyautogui.hotkey") as mock_hotkey:
            res = self.wm.manage_window("Chrome", "snap_right")
            self.assertEqual(res["status"], "SUCCESS")
            mock_hotkey.assert_called_with("win", "right")


if __name__ == "__main__":
    unittest.main()
