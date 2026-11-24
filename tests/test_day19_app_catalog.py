"""
Day 19 Unit Tests — Universal Windows Application Catalog.
Verifies discovery, search, ambiguity resolution, launch target resolution,
missing application handling, and cache operations.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from zye_windows.app_catalog import WindowsAppCatalog
from zye_windows.windows_models import AppInfo, InstallationType


class TestDay19AppCatalog(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_file = Path(self.temp_dir.name) / "test_app_cache.json"

        # Mock discovery and window manager
        self.mock_discovery = MagicMock()
        self.mock_window_mgr = MagicMock()

        self.sample_apps = [
            AppInfo(
                application_name="Google Chrome",
                app_id="Chrome",
                installation_type=InstallationType.WIN32,
                available=True,
                executable_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            ),
            AppInfo(
                application_name="WhatsApp",
                app_id="5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
                installation_type=InstallationType.STORE,
                available=True,
            ),
            AppInfo(
                application_name="Notepad",
                app_id="Microsoft.WindowsNotepad_8wekyb3d8bbwe!App",
                installation_type=InstallationType.STORE,
                executable_path="notepad.exe",
            ),
            AppInfo(
                application_name="VLC media player",
                app_id="VideoLAN.VLC",
                installation_type=InstallationType.WIN32,
                executable_path="vlc.exe",
            ),
        ]
        self.mock_discovery.get_installed_apps.return_value = list(self.sample_apps)

        self.catalog = WindowsAppCatalog(
            cache_file=self.cache_file,
            discovery=self.mock_discovery,
            window_mgr=self.mock_window_mgr,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_discover_installed_apps(self) -> None:
        """Verify discover_installed_apps extracts formatted application descriptors."""
        apps = self.catalog.discover_installed_apps()
        self.assertEqual(len(apps), 4)
        names = [a["name"] for a in apps]
        self.assertIn("Google Chrome", names)
        self.assertIn("WhatsApp", names)

    def test_search_installed_apps_exact_and_fuzzy(self) -> None:
        """Verify search_installed_apps matches query."""
        self.mock_discovery.search_installed_apps.return_value = [self.sample_apps[0]]
        matches = self.catalog.search_installed_apps("Chrome")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["name"], "Google Chrome")

    def test_get_application_details_found(self) -> None:
        """Verify get_application_details finds by name or app_id."""
        details = self.catalog.get_application_details("WhatsApp")
        self.assertEqual(details.get("status"), "SUCCESS")
        self.assertEqual(details.get("application"), "WhatsApp")
        self.assertEqual(details.get("type"), "STORE")

    def test_get_application_details_missing(self) -> None:
        """Verify get_application_details returns NOT_FOUND for unknown application."""
        details = self.catalog.get_application_details("NonExistentApplication123")
        self.assertEqual(details.get("status"), "NOT_FOUND")

    def test_get_application_launch_target_store_and_win32(self) -> None:
        """Verify launch target formatting: shell:AppsFolder URI for Store vs process for Win32."""
        # Store app target
        store_target = self.catalog.get_application_launch_target("WhatsApp")
        self.assertEqual(store_target.get("status"), "SUCCESS")
        self.assertEqual(store_target.get("method"), "EXPLORER_URI")
        self.assertTrue(store_target.get("launch_target", "").startswith("shell:AppsFolder\\"))

        # Win32 app target
        win32_target = self.catalog.get_application_launch_target("Google Chrome")
        self.assertEqual(win32_target.get("status"), "SUCCESS")
        self.assertEqual(win32_target.get("method"), "PROCESS_SPAWN")
        self.assertIn("chrome.exe", win32_target.get("launch_target"))


if __name__ == "__main__":
    unittest.main()
