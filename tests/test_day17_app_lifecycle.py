"""
Unit tests for WindowsAppLifecycle (Day 17).
Verifies application launch orchestration, window registration polling, graceful closing,
restart cycles, and end-to-end application health reporting.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_windows.app_lifecycle import WindowsAppLifecycle


class TestDay17AppLifecycle(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_launcher = MagicMock()
        self.mock_window_mgr = MagicMock()
        self.mock_process_mgr = MagicMock()

        self.lifecycle = WindowsAppLifecycle(
            app_launcher=self.mock_launcher,
            window_manager=self.mock_window_mgr,
            process_manager=self.mock_process_mgr,
        )

    def test_launch_application(self) -> None:
        """Verify launch_application delegates to launcher."""
        self.mock_launcher.open_any_app.return_value = {"status": "LAUNCHED", "app_name": "notepad"}
        res = self.lifecycle.launch_application("notepad", timeout=5.0)
        self.assertEqual(res.get("status"), "LAUNCHED")
        self.mock_launcher.open_any_app.assert_called_once_with(app_name="notepad", timeout=5.0)

    def test_wait_for_application_found(self) -> None:
        """Verify wait_for_application finds visible window."""
        self.mock_window_mgr.list_windows.return_value = [
            {"title": "Untitled - Notepad", "hwnd": 12345}
        ]
        res = self.lifecycle.wait_for_application("notepad", timeout=1.0)
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertTrue(res.get("window_found"))

    def test_wait_for_application_timeout(self) -> None:
        """Verify wait_for_application returns TIMEOUT when window doesn't appear."""
        self.mock_window_mgr.list_windows.return_value = []
        res = self.lifecycle.wait_for_application("notepad", timeout=0.2)
        self.assertEqual(res.get("status"), "TIMEOUT")
        self.assertFalse(res.get("window_found"))

    def test_get_application_status(self) -> None:
        """Verify application status aggregation across process and window managers."""
        self.mock_process_mgr.is_app_running.return_value = True
        self.mock_process_mgr.find_process_by_name.return_value = [{"pid": 5000, "name": "notepad.exe"}]
        self.mock_process_mgr.check_process_responsiveness.return_value = {"is_responsive": True}
        self.mock_window_mgr.list_windows.return_value = [{"title": "Notepad", "hwnd": 54321}]

        res = self.lifecycle.get_application_status("notepad")
        self.assertTrue(res.get("is_running"))
        self.assertTrue(res.get("is_responsive"))
        self.assertTrue(res.get("has_window"))
        self.assertEqual(res.get("primary_pid"), 5000)

    def test_close_application_gracefully_not_running(self) -> None:
        """Verify graceful close when app is not running."""
        self.mock_process_mgr.find_process_by_name.return_value = []
        self.mock_process_mgr.is_app_running.return_value = False

        res = self.lifecycle.close_application_gracefully("notepad")
        self.assertEqual(res.get("status"), "NOT_RUNNING")

    def test_get_application_health(self) -> None:
        """Verify health check returns HEALTHY when responsive and resource usage succeeds."""
        self.mock_process_mgr.is_app_running.return_value = True
        self.mock_process_mgr.find_process_by_name.return_value = [{"pid": 5000, "name": "notepad.exe"}]
        self.mock_process_mgr.check_process_responsiveness.return_value = {"is_responsive": True}
        self.mock_process_mgr.get_process_resource_usage.return_value = {"status": "SUCCESS", "memory_mb": 25.0}

        res = self.lifecycle.get_application_health("notepad")
        self.assertEqual(res.get("status"), "RUNNING")
        self.assertEqual(res.get("health"), "HEALTHY")


if __name__ == "__main__":
    unittest.main()
