"""Day 16 Unit Tests — Universal Windows Application Discovery & Caching."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from zye_windows.app_discovery import WindowsAppDiscovery
from zye_windows.windows_models import AppInfo, InstallationType


class TestWindowsAppDiscovery(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_file = Path(self.temp_dir.name) / "app_cache.json"
        self.discovery = WindowsAppDiscovery(cache_file=self.cache_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initialization(self):
        self.assertIsNotNone(self.discovery)
        self.assertEqual(self.discovery.cache_file, self.cache_file)

    def test_save_and_load_cache(self):
        sample_apps = [
            AppInfo(application_name="WhatsApp", app_id="whatsapp", installation_type=InstallationType.STORE),
            AppInfo(application_name="Google Chrome", app_id="chrome", installation_type=InstallationType.WIN32),
        ]
        self.discovery._save_to_disk_cache(sample_apps)
        self.assertTrue(self.cache_file.exists())

        loaded = self.discovery.get_installed_apps(force_refresh=False)
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].application_name, "WhatsApp")
        self.assertEqual(loaded[1].application_name, "Google Chrome")

    @patch("subprocess.run")
    def test_discover_apps_via_powershell(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([
                {"Name": "WhatsApp", "AppID": "5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App"},
                {"Name": "Visual Studio Code", "AppID": "Microsoft.VisualStudioCode"}
            ]),
            stderr=""
        )
        apps = self.discovery.get_installed_apps(force_refresh=True)
        self.assertGreaterEqual(len(apps), 2)
        names = [a.application_name for a in apps]
        self.assertIn("WhatsApp", names)

    @patch("subprocess.run")
    def test_discover_fallback_on_powershell_failure(self, mock_run):
        mock_run.side_effect = Exception("PowerShell execution failed")
        apps = self.discovery.get_installed_apps(force_refresh=True)
        self.assertGreater(len(apps), 0)
        # Should include well-known apps
        names = [a.application_name.lower() for a in apps]
        self.assertTrue(any("whatsapp" in n for n in names))
        self.assertTrue(any("chrome" in n for n in names))

    def test_find_application_matches(self):
        import time
        self.discovery._last_loaded_time = time.monotonic()
        self.discovery._memory_cache = [
            AppInfo(application_name="WhatsApp", app_id="whatsapp", installation_type=InstallationType.STORE),
            AppInfo(application_name="Google Chrome", app_id="chrome", installation_type=InstallationType.WIN32),
            AppInfo(application_name="Notepad", app_id="notepad", installation_type=InstallationType.WIN32),
        ]
        matches = self.discovery.search_installed_apps("what")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].application_name, "WhatsApp")

    def test_find_application_not_found(self):
        import time
        self.discovery._last_loaded_time = time.monotonic()
        self.discovery._memory_cache = [
            AppInfo(application_name="WhatsApp", app_id="whatsapp", installation_type=InstallationType.STORE),
        ]
        matches = self.discovery.search_installed_apps("NonExistentApplication12345")
        self.assertEqual(len(matches), 0)


if __name__ == "__main__":
    unittest.main()
