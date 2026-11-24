"""Day 16 Unit Tests — Global Media Session Controller."""
import unittest
from unittest.mock import MagicMock, patch

from zye_windows.media_controller import WindowsMediaController


class TestWindowsMediaController(unittest.TestCase):
    def setUp(self):
        self.mc = WindowsMediaController()

    def test_unsupported_command(self):
        res = self.mc.media_control("fast_forward_double_time")
        self.assertEqual(res["status"], "REJECTED")

    @patch("pyautogui.press")
    def test_play_pause(self, mock_press):
        res = self.mc.media_control("play_pause")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["command"], "play_pause")
        mock_press.assert_called_with("playpause")

    @patch("pyautogui.press")
    def test_next_track(self, mock_press):
        res = self.mc.media_control("next")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["command"], "next")
        mock_press.assert_called_with("nexttrack")

    @patch("pyautogui.press")
    def test_prev_track(self, mock_press):
        res = self.mc.media_control("previous")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["command"], "previous")
        mock_press.assert_called_with("prevtrack")

    @patch("pyautogui.press")
    def test_stop(self, mock_press):
        res = self.mc.media_control("stop")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["command"], "stop")
        mock_press.assert_called_with("stop")


if __name__ == "__main__":
    unittest.main()
