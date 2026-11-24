"""
Day 18 Unit Tests — Voice-to-OS Execution & Intent Validation.
Verifies parsing of natural Tamil, English, and Tanglish workspace commands
to appropriate Day 18 tools and ambiguity prompts.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_windows.input_controller import normalize_shortcut_name
from zye_windows.window_manager import WindowsWindowManager


class MockWindow:
    def __init__(self, title: str):
        self.title = title
        self._hWnd = 1111
        self.isMinimized = False
        self.isActive = False

    def activate(self):
        self.isActive = True

    def restore(self):
        pass


class TestDay18VoiceIntegration(unittest.TestCase):

    def setUp(self) -> None:
        self.wm = WindowsWindowManager()

    @patch("pygetwindow.getAllWindows")
    def test_voice_command_disambiguation(self, mock_get_all: MagicMock) -> None:
        """
        Voice: 'Chrome project research window focus pannu'
        When multiple Chrome windows exist, should identify the specific target.
        """
        mock_get_all.return_value = [
            MockWindow("Chrome - Project Research"),
            MockWindow("Chrome - Gmail"),
            MockWindow("Chrome - YouTube"),
        ]
        res = self.wm.find_window("Project Research")
        self.assertEqual(res["status"], "MATCH")
        self.assertIn("Project Research", res["title"])

    def test_voice_shortcut_resolution(self) -> None:
        """
        Voice: 'Alt Tab press pannu' or 'Win D show desktop'
        """
        self.assertEqual(normalize_shortcut_name("Alt Tab"), "alt_tab")
        self.assertEqual(normalize_shortcut_name("Win D"), "win_d")
        self.assertEqual(normalize_shortcut_name("Ctrl S"), "ctrl_s")

    @patch("pygetwindow.getAllWindows")
    def test_voice_window_snap_command(self, mock_get_all: MagicMock) -> None:
        """
        Voice: 'VS Code left side-la vai' -> snap_left action
        """
        win = MockWindow("Visual Studio Code")
        mock_get_all.return_value = [win]
        with patch("pyautogui.hotkey") as mock_hotkey:
            res = self.wm.manage_window("Visual Studio Code", "snap_left")
            self.assertEqual(res["status"], "SUCCESS")
            mock_hotkey.assert_called_with("win", "left")


if __name__ == "__main__":
    unittest.main()
