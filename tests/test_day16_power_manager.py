"""Day 16 Unit Tests — Windows Power Management & Battery Telemetry."""
import sys
import unittest
from unittest.mock import MagicMock, patch

from zye_windows.power_manager import WindowsPowerManager


class TestWindowsPowerManager(unittest.TestCase):
    def setUp(self):
        self.pm = WindowsPowerManager()

    def test_unsupported_power_action(self):
        res = self.pm.power_action("hyperdrive")
        self.assertEqual(res["status"], "REJECTED")

    @patch("ctypes.windll.user32.LockWorkStation", return_value=1)
    def test_lock_workstation(self, mock_lock):
        if sys.platform != "win32":
            self.skipTest("Windows-only test")
        res = self.pm.power_action("lock")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["action"], "lock")

    def test_shutdown_unconfirmed_blocked(self):
        res = self.pm.power_action("shutdown", confirmed=False)
        self.assertEqual(res["status"], "CONFIRMATION_REQUIRED")
        self.assertTrue(res["requires_user_confirmation"])

    def test_restart_unconfirmed_blocked(self):
        res = self.pm.power_action("restart", confirmed=False)
        self.assertEqual(res["status"], "CONFIRMATION_REQUIRED")
        self.assertTrue(res["requires_user_confirmation"])

    @patch("subprocess.run")
    def test_shutdown_confirmed_scheduled(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        res = self.pm.power_action("shutdown", confirmed=True)
        self.assertEqual(res["status"], "SCHEDULED")
        self.assertEqual(res["cancellation_window_seconds"], 30)
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("/s", cmd)
        self.assertIn("/t", cmd)

    @patch("subprocess.run")
    def test_restart_confirmed_scheduled(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        res = self.pm.power_action("restart", confirmed=True)
        self.assertEqual(res["status"], "SCHEDULED")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("/r", cmd)

    @patch("subprocess.run")
    def test_cancel_shutdown(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        res = self.pm.cancel_shutdown()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("cancelled", res["message"])
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("/a", cmd)

    @patch("psutil.sensors_battery")
    def test_get_battery_status_available(self, mock_sensors):
        mock_batt = MagicMock()
        mock_batt.percent = 85.0
        mock_batt.power_plugged = True
        mock_batt.secsleft = -1
        mock_sensors.return_value = mock_batt

        res = self.pm.get_battery_status()
        self.assertIn(res["status"], ("CHARGING", "DISCHARGING", "FULL", "UNKNOWN"))
        self.assertEqual(res["percent"], 85.0)
        self.assertTrue(res["is_plugged"])


if __name__ == "__main__":
    unittest.main()
