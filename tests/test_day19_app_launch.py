"""
Day 19 Unit Tests — Application Launch & Window Verification.
Verifies launching Win32 and Store applications, reusing existing instances,
timeout handling, and window responsiveness verification.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_windows.app_catalog import WindowsAppCatalog
from zye_windows.windows_models import AppInfo, InstallationType


class TestDay19AppLaunch(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_discovery = MagicMock()
        self.mock_window_mgr = MagicMock()
        self.mock_launcher = MagicMock()

        self.catalog = WindowsAppCatalog(
            discovery=self.mock_discovery,
            launcher=self.mock_launcher,
            window_mgr=self.mock_window_mgr,
        )

    def test_launch_application_delegation(self) -> None:
        """Verify launch_application delegates to launcher with timeout."""
        self.mock_launcher.open_any_app.return_value = {
            "status": "LAUNCHED",
            "application": "Notepad",
            "verified": True,
        }
        res = self.catalog.launch_application("Notepad", timeout=12.0)
        self.assertEqual(res.get("status"), "LAUNCHED")
        self.mock_launcher.open_any_app.assert_called_once_with("Notepad", timeout=12.0)

    def test_verify_application_launch_success(self) -> None:
        """Verify verify_application_launch discovers running window."""
        mock_win = MagicMock()
        mock_win.title = "Notepad - Untitled"
        mock_win._hWnd = 12345
        self.mock_window_mgr.find_windows.return_value = [mock_win]

        res = self.catalog.verify_application_launch("Notepad", timeout=1.0)
        self.assertEqual(res.get("status"), "VERIFIED")
        self.assertTrue(res.get("is_running"))
        self.assertEqual(res.get("hwnd"), 12345)

    def test_verify_application_launch_timeout(self) -> None:
        """Verify verify_application_launch returns UNVERIFIED on timeout when no window found."""
        self.mock_window_mgr.find_windows.return_value = []

        res = self.catalog.verify_application_launch("GhostApp", timeout=0.1)
        self.assertEqual(res.get("status"), "UNVERIFIED")
        self.assertFalse(res.get("is_running"))

    def test_launch_empty_identifier(self) -> None:
        """Verify verify_application_launch rejects empty identifier."""
        res = self.catalog.verify_application_launch("")
        self.assertEqual(res.get("status"), "ERROR")


if __name__ == "__main__":
    unittest.main()
