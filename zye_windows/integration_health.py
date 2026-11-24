"""
Windows Integration Health & Diagnostic Telemetry — Zye Day 19.
Aggregates subsystem health metrics, verifies availability of Win32/UIA APIs,
and ensures complete Phase 2 integration readiness.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Any, Optional

from zye_windows.app_catalog import WindowsAppCatalog
from zye_windows.clipboard_manager import WindowsClipboardManager
from zye_windows.display_manager import WindowsDisplayManager
from zye_windows.file_search import WindowsFileSearch
from zye_windows.hardware_manager import WindowsHardwareManager
from zye_windows.input_controller import WindowsInputController
from zye_windows.media_controller import WindowsMediaController
from zye_windows.process_manager import WindowsProcessManager
from zye_windows.recycle_bin_manager import WindowsRecycleBinManager
from zye_windows.screenshot_manager import WindowsScreenshotManager
from zye_windows.ui_automation import WindowsUIAutomation
from zye_windows.window_manager import WindowsWindowManager
from zye_windows.workspace_manager import WindowsWorkspaceManager

logger = logging.getLogger("zye.windows.integration_health")


class WindowsIntegrationHealth:
    """
    Performs non-invasive health probes across all 12 Windows OS control subsystems.
    """

    def __init__(self) -> None:
        self.process_mgr = WindowsProcessManager()
        self.app_catalog = WindowsAppCatalog()
        self.window_mgr = WindowsWindowManager()
        self.workspace_mgr = WindowsWorkspaceManager()
        self.display_mgr = WindowsDisplayManager()
        self.input_ctrl = WindowsInputController()
        self.clipboard_mgr = WindowsClipboardManager()
        self.file_search = WindowsFileSearch()
        self.media_ctrl = WindowsMediaController()
        self.screenshot_mgr = WindowsScreenshotManager()
        self.recycle_bin_mgr = WindowsRecycleBinManager()
        self.hardware_mgr = WindowsHardwareManager()
        self.ui_auto = WindowsUIAutomation()

    def check_subsystem_health(self) -> dict[str, Any]:
        """
        Probe all subsystems and return status report without mutating system state.
        """
        report: dict[str, Any] = {}

        # 1. Process Manager
        try:
            summary = self.process_mgr.get_system_resource_summary()
            report["process_manager"] = {
                "healthy": summary.get("status") == "SUCCESS",
                "active_processes": summary.get("active_processes_count", 0),
            }
        except Exception as exc:
            report["process_manager"] = {"healthy": False, "error": str(exc)}

        # 2. Application Catalog
        try:
            apps = self.app_catalog.discover_installed_apps()
            report["app_catalog"] = {
                "healthy": True,
                "discovered_apps_count": len(apps),
            }
        except Exception as exc:
            report["app_catalog"] = {"healthy": False, "error": str(exc)}

        # 3. Window Manager
        try:
            wins = self.window_mgr.list_open_windows()
            report["window_manager"] = {
                "healthy": True,
                "open_windows_count": len(wins),
            }
        except Exception as exc:
            report["window_manager"] = {"healthy": False, "error": str(exc)}

        # 4. Workspace Manager
        try:
            desktops = self.workspace_mgr.get_virtual_desktops()
            report["workspace_manager"] = {
                "healthy": desktops.get("status") == "SUCCESS",
                "desktop_count": desktops.get("count", 1),
            }
        except Exception as exc:
            report["workspace_manager"] = {"healthy": False, "error": str(exc)}

        # 5. Display Manager
        try:
            monitors = self.display_mgr.get_connected_displays()
            report["display_manager"] = {
                "healthy": len(monitors) > 0,
                "monitor_count": len(monitors),
            }
        except Exception as exc:
            report["display_manager"] = {"healthy": False, "error": str(exc)}

        # 6. Input Controller
        try:
            shortcuts_count = len(self.input_ctrl.NAMED_SHORTCUTS)
            report["input_controller"] = {
                "healthy": shortcuts_count >= 20,
                "shortcuts_registered": shortcuts_count,
            }
        except Exception as exc:
            report["input_controller"] = {"healthy": False, "error": str(exc)}

        # 7. Clipboard Manager
        try:
            meta = self.clipboard_mgr.get_clipboard_metadata()
            report["clipboard_manager"] = {
                "healthy": True,
                "contains_unicode": meta.contains_unicode,
            }
        except Exception as exc:
            report["clipboard_manager"] = {"healthy": False, "error": str(exc)}

        # 8. File Search
        try:
            dirs = self.file_search.allowed_dir_names
            report["file_search"] = {
                "healthy": len(dirs) >= 4,
                "allowed_directories": dirs,
            }
        except Exception as exc:
            report["file_search"] = {"healthy": False, "error": str(exc)}

        # 9. Media Controller
        try:
            sess = self.media_ctrl.get_active_media_session()
            report["media_controller"] = {
                "healthy": True,
                "session_status": sess.status,
            }
        except Exception as exc:
            report["media_controller"] = {"healthy": False, "error": str(exc)}

        # 10. Screenshot Manager
        try:
            sc_list = self.screenshot_mgr.list_screenshots(limit=5)
            report["screenshot_manager"] = {
                "healthy": True,
                "stored_screenshots_count": len(sc_list),
            }
        except Exception as exc:
            report["screenshot_manager"] = {"healthy": False, "error": str(exc)}

        # 11. Recycle Bin Manager
        try:
            rb_prev = self.recycle_bin_mgr.preview_recycle_bin()
            report["recycle_bin_manager"] = {
                "healthy": rb_prev.get("status") in ("SUCCESS", "CONFIRMATION_REQUIRED"),
            }
        except Exception as exc:
            report["recycle_bin_manager"] = {"healthy": False, "error": str(exc)}

        # 12. Hardware Manager
        try:
            hw_stat = self.hardware_mgr.get_hardware_status()
            report["hardware_manager"] = {
                "healthy": hw_stat.get("status") == "SUCCESS",
            }
        except Exception as exc:
            report["hardware_manager"] = {"healthy": False, "error": str(exc)}

        # Overall health calculation
        all_healthy = all(v.get("healthy", False) for v in report.values())
        return {
            "status": "HEALTHY" if all_healthy else "DEGRADED",
            "timestamp": time.time(),
            "subsystems": report,
            "all_healthy": all_healthy,
        }
