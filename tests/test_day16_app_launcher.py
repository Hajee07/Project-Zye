"""Day 16 Unit Tests — Universal Windows Application Launcher."""
import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from zye_windows.app_discovery import WindowsAppDiscovery
from zye_windows.app_launcher import WindowsAppLauncher
from zye_windows.window_manager import WindowsWindowManager
from zye_windows.windows_models import AppInfo, InstallationType


class TestWindowsAppLauncher(unittest.TestCase):
    def setUp(self):
        self.discovery = MagicMock(spec=WindowsAppDiscovery)
        self.window_mgr = MagicMock(spec=WindowsWindowManager)
        self.launcher = WindowsAppLauncher(discovery=self.discovery, window_mgr=self.window_mgr)

    def test_app_not_found(self):
        self.discovery.search_installed_apps.return_value = []
        res = self.launcher.open_any_app("NonExistentApp")
        self.assertEqual(res["status"], "APP_NOT_FOUND")

    def test_app_already_running(self):
        app = AppInfo(application_name="WhatsApp", app_id="whatsapp", installation_type=InstallationType.STORE)
        self.discovery.search_installed_apps.return_value = [app]

        mock_win = MagicMock()
        mock_win.title = "WhatsApp"
        mock_win._hWnd = 1234
        self.window_mgr.find_windows.return_value = [mock_win]

        res = self.launcher.open_any_app("whatsapp")
        self.assertEqual(res["status"], "ALREADY_RUNNING")
        self.assertTrue(res["verified"])
        self.window_mgr.manage_window.assert_called_with("WhatsApp", "focus")

    @patch("subprocess.Popen")
    def test_launch_app_success(self, mock_popen):
        app = AppInfo(application_name="WhatsApp", app_id="5319275A.WhatsAppDesktop", installation_type=InstallationType.STORE)
        self.discovery.search_installed_apps.return_value = [app]

        mock_win = MagicMock()
        mock_win.title = "WhatsApp"
        mock_win._hWnd = 5678

        # First call in already_running check returns empty, second call in verification loop returns mock_win
        self.window_mgr.find_windows.side_effect = [[], [mock_win]]

        res = self.launcher.open_any_app("whatsapp", timeout=2.0)
        self.assertEqual(res["status"], "LAUNCHED")
        self.assertTrue(res["verified"])
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        self.assertIn("shell:AppsFolder\\5319275A.WhatsAppDesktop", cmd[1])

    def test_launch_failure_handling(self):
        app = AppInfo(application_name="Calculator", app_id="calc", installation_type=InstallationType.STORE)
        self.discovery.search_installed_apps.return_value = [app]
        self.window_mgr.find_windows.return_value = []

        with patch.object(self.launcher, "_launch_app_process", return_value=(False, "Permission denied")):
            res = self.launcher.open_any_app("calc")
            self.assertEqual(res["status"], "APP_LAUNCH_FAILED")
            self.assertIn("Permission denied", res["message"])


if __name__ == "__main__":
    unittest.main()
