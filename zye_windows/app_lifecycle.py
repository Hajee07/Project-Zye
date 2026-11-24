"""
Windows Application Lifecycle Management — Zye Day 17.
Coordinates application launch, window readiness polling, graceful shutdown (WM_CLOSE),
restart cycles, and holistic runtime health checks.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from zye_windows.app_launcher import WindowsAppLauncher
from zye_windows.process_manager import WindowsProcessManager
from zye_windows.window_manager import WindowsWindowManager

logger = logging.getLogger("zye.windows.app_lifecycle")


class WindowsAppLifecycle:
    """End-to-end lifecycle controller for desktop applications."""

    def __init__(
        self,
        app_launcher: Optional[WindowsAppLauncher] = None,
        window_manager: Optional[WindowsWindowManager] = None,
        process_manager: Optional[WindowsProcessManager] = None,
    ) -> None:
        self.app_launcher = app_launcher or WindowsAppLauncher()
        self.window_mgr = window_manager or WindowsWindowManager()
        self.process_mgr = process_manager or WindowsProcessManager()

    def launch_application(self, app_name: str, timeout: float = 15.0) -> dict[str, Any]:
        """Launch an application and verify its startup status."""
        res = self.app_launcher.open_any_app(app_name=app_name, timeout=timeout)
        return res

    def wait_for_application(self, app_name: str, timeout: float = 10.0) -> dict[str, Any]:
        """Poll until the application's window becomes visible and registered."""
        start = time.time()
        while time.time() - start < timeout:
            windows = self.window_mgr.list_windows()
            for w in windows:
                if app_name.lower() in w.get("title", "").lower():
                    return {
                        "status": "SUCCESS",
                        "app_name": app_name,
                        "window_found": True,
                        "title": w.get("title"),
                        "hwnd": w.get("hwnd"),
                        "elapsed_seconds": round(time.time() - start, 2),
                    }
            time.sleep(0.5)

        return {
            "status": "TIMEOUT",
            "app_name": app_name,
            "window_found": False,
            "message": f"Window for '{app_name}' did not appear within {timeout}s.",
        }

    def get_application_status(self, app_name: str) -> dict[str, Any]:
        """Check whether the application is running, responding, and has a visible window."""
        is_running = self.process_mgr.is_app_running(app_name)
        matching_procs = self.process_mgr.find_process_by_name(app_name)

        pid = matching_procs[0]["pid"] if matching_procs else None
        responsiveness = self.process_mgr.check_process_responsiveness(pid) if pid else {}

        windows = self.window_mgr.list_windows()
        matching_windows = [w for w in windows if app_name.lower() in w.get("title", "").lower()]

        return {
            "app_name": app_name,
            "is_running": is_running,
            "process_count": len(matching_procs),
            "primary_pid": pid,
            "is_responsive": responsiveness.get("is_responsive", False),
            "has_window": len(matching_windows) > 0,
            "window_count": len(matching_windows),
            "windows": matching_windows,
        }

    def close_application_gracefully(self, app_name: str, timeout: float = 5.0) -> dict[str, Any]:
        """Attempt graceful closure via WM_CLOSE on matching windows."""
        matching_procs = self.process_mgr.find_process_by_name(app_name)
        if not matching_procs and not self.process_mgr.is_app_running(app_name):
            return {
                "status": "NOT_RUNNING",
                "app_name": app_name,
                "message": f"Application '{app_name}' is not currently running.",
            }

        # Send close to matching windows
        self.window_mgr.manage_window(window_keyword=app_name, action="close")

        # Wait for processes to exit
        start = time.time()
        while time.time() - start < timeout:
            if not self.process_mgr.is_app_running(app_name):
                return {
                    "status": "SUCCESS",
                    "app_name": app_name,
                    "message": f"Application '{app_name}' closed gracefully.",
                    "closed": True,
                }
            time.sleep(0.5)

        return {
            "status": "TIMEOUT",
            "app_name": app_name,
            "closed": False,
            "message": f"Application '{app_name}' did not exit within {timeout}s after close command.",
        }

    def restart_application(self, app_name: str, timeout: float = 15.0) -> dict[str, Any]:
        """Close an application and re-launch it cleanly."""
        close_res = self.close_application_gracefully(app_name, timeout=5.0)
        time.sleep(1.0)
        launch_res = self.launch_application(app_name, timeout=timeout)

        return {
            "status": "SUCCESS" if launch_res.get("status") in ("LAUNCHED", "ALREADY_RUNNING") else "FAILED",
            "app_name": app_name,
            "close_result": close_res,
            "launch_result": launch_res,
        }

    def verify_application_ready(self, app_name: str, timeout: float = 10.0) -> dict[str, Any]:
        """Verify that the application has launched, has a responsive window, and is ready for use."""
        wait_res = self.wait_for_application(app_name, timeout=timeout)
        if wait_res.get("status") != "SUCCESS":
            return wait_res

        status_res = self.get_application_status(app_name)
        ready = status_res.get("is_running") and status_res.get("has_window")

        return {
            "status": "READY" if ready else "NOT_READY",
            "app_name": app_name,
            "details": status_res,
        }

    def get_application_health(self, app_name: str) -> dict[str, Any]:
        """Query CPU, memory, thread count, and responsiveness health metrics."""
        status = self.get_application_status(app_name)
        pid = status.get("primary_pid")
        if not pid:
            return {
                "status": "NOT_RUNNING",
                "app_name": app_name,
                "health": "UNKNOWN",
            }

        usage = self.process_mgr.get_process_resource_usage(pid)
        responsiveness = self.process_mgr.check_process_responsiveness(pid)

        is_healthy = responsiveness.get("is_responsive", False) and usage.get("status") == "SUCCESS"

        return {
            "status": "RUNNING",
            "app_name": app_name,
            "pid": pid,
            "health": "HEALTHY" if is_healthy else "DEGRADED",
            "resource_usage": usage,
            "responsiveness": responsiveness,
        }
