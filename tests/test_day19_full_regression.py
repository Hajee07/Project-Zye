"""
Day 19 Unit Tests — Full Phase 2 Windows OS Control Cross-Module Regression.
Validates interoperability between ProcessManager, AppCatalog, UIAutomation,
ApplicationController, WindowManager, WorkspaceManager, DisplayManager,
InputController, ClipboardManager, FileSearch, MediaController,
ScreenshotManager, RecycleBinManager, and HardwareManager.
"""

from __future__ import annotations

import unittest

from zye_windows.integration_health import WindowsIntegrationHealth
from zye_windows.os_integration import WindowsOSIntegration


class TestDay19FullRegression(unittest.TestCase):

    def setUp(self) -> None:
        self.os_int = WindowsOSIntegration()
        self.health = WindowsIntegrationHealth()

    def test_integration_health_all_probed(self) -> None:
        """Verify integration health reports status across all 12 subsystems."""
        status = self.health.check_subsystem_health()
        self.assertIn(status.get("status"), ("HEALTHY", "DEGRADED"))
        subsystems = status.get("subsystems", {})
        expected_subs = [
            "process_manager", "app_catalog", "window_manager", "workspace_manager",
            "display_manager", "input_controller", "clipboard_manager", "file_search",
            "media_controller", "screenshot_manager", "recycle_bin_manager", "hardware_manager",
        ]
        for s in expected_subs:
            self.assertIn(s, subsystems, f"Subsystem '{s}' should be probed")

    def test_os_integration_facade_methods(self) -> None:
        """Verify Master OS integration facade binds core subsystem methods."""
        # Window & Workspace
        self.assertTrue(callable(getattr(self.os_int, "list_windows")))
        self.assertTrue(callable(getattr(self.os_int, "get_virtual_desktops")))
        self.assertTrue(callable(getattr(self.os_int, "get_connected_displays")))

        # Input & Clipboard
        self.assertTrue(callable(getattr(self.os_int, "execute_shortcut")))
        self.assertTrue(callable(getattr(self.os_int, "get_clipboard_metadata")))

        # File & Media & Utilities
        self.assertTrue(callable(getattr(self.os_int, "search_files")))
        self.assertTrue(callable(getattr(self.os_int, "get_media_session")))
        self.assertTrue(callable(getattr(self.os_int, "capture_screenshot")))
        self.assertTrue(callable(getattr(self.os_int, "get_hardware_status")))

        # Process & Application
        self.assertTrue(callable(getattr(self.os_int, "list_processes")))
        self.assertTrue(callable(getattr(self.os_int, "open_app")))


if __name__ == "__main__":
    unittest.main()
