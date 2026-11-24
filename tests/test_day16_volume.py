"""Day 16 Unit Tests — Master Audio Volume & Page Scrolling Engine."""
import unittest
from unittest.mock import MagicMock, patch

from zye_windows.volume_manager import WindowsVolumeManager


class TestWindowsVolumeManager(unittest.TestCase):
    def setUp(self):
        self.vm = WindowsVolumeManager()

    def test_unsupported_volume_action(self):
        res = self.vm.control_volume("blast_speakers")
        self.assertEqual(res["status"], "REJECTED")

    @patch("pyautogui.press")
    def test_volume_up(self, mock_press):
        res = self.vm.control_volume("up", steps=3)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["action"], "up")
        self.assertEqual(mock_press.call_count, 3)
        mock_press.assert_called_with("volumeup")

    @patch("pyautogui.press")
    def test_volume_down(self, mock_press):
        res = self.vm.control_volume("down", steps=2)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["action"], "down")
        self.assertEqual(mock_press.call_count, 2)
        mock_press.assert_called_with("volumedown")

    @patch("pyautogui.press")
    def test_volume_mute(self, mock_press):
        res = self.vm.control_volume("mute")
        self.assertEqual(res["status"], "SUCCESS")
        mock_press.assert_called_with("volumemute")

    def test_set_volume_percent_out_of_range(self):
        res_neg = self.vm.set_volume_percent(-5)
        self.assertEqual(res_neg["status"], "REJECTED")
        res_high = self.vm.set_volume_percent(105)
        self.assertEqual(res_high["status"], "REJECTED")

    @patch("pyautogui.press")
    def test_set_volume_percent_success(self, mock_press):
        res = self.vm.set_volume_percent(50)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["level"], 50)
        # 50 down presses + 25 up presses = 75 presses
        self.assertEqual(mock_press.call_count, 75)

    def test_scroll_page_invalid_direction(self):
        res = self.vm.scroll_page("sideways")
        self.assertEqual(res["status"], "REJECTED")

    @patch("pyautogui.scroll")
    def test_scroll_page_down(self, mock_scroll):
        res = self.vm.scroll_page("down", amount=5)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["direction"], "down")
        mock_scroll.assert_called_with(-600)

    @patch("pyautogui.scroll")
    def test_scroll_page_up(self, mock_scroll):
        res = self.vm.scroll_page("up", amount=4)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["direction"], "up")
        mock_scroll.assert_called_with(480)


if __name__ == "__main__":
    unittest.main()
