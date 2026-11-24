"""Day 16 Unit Tests — Screen Brightness Control Engine."""
import sys
import unittest
from unittest.mock import MagicMock, patch

from zye_windows.brightness_manager import WindowsBrightnessManager


class TestWindowsBrightnessManager(unittest.TestCase):
    def setUp(self):
        self.bm = WindowsBrightnessManager()

    def test_invalid_type_rejected(self):
        res = self.bm.set_brightness("not_a_number")
        self.assertEqual(res["status"], "ERROR")

    def test_negative_level_rejected(self):
        res = self.bm.set_brightness(-15)
        self.assertEqual(res["status"], "REJECTED")

    def test_over_100_level_rejected(self):
        res = self.bm.set_brightness(120)
        self.assertEqual(res["status"], "REJECTED")

    @patch("subprocess.run")
    def test_set_brightness_success(self, mock_run):
        if sys.platform != "win32":
            self.skipTest("Windows-only test")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        res = self.bm.set_brightness(65)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["level"], 65)
        self.assertTrue(res["verified"])

    @patch("subprocess.run")
    def test_set_brightness_unsupported_hardware(self, mock_run):
        if sys.platform != "win32":
            self.skipTest("Windows-only test")
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Get-WmiObject : Not found")
        res = self.bm.set_brightness(50)
        self.assertEqual(res["status"], "HARDWARE_NOT_SUPPORTED")

    @patch("subprocess.run")
    def test_get_brightness_success(self, mock_run):
        if sys.platform != "win32":
            self.skipTest("Windows-only test")
        mock_run.return_value = MagicMock(returncode=0, stdout="75\n", stderr="")
        res = self.bm.get_brightness()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["current_brightness"], 75)


if __name__ == "__main__":
    unittest.main()
