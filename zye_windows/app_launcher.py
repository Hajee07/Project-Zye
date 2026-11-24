"""
Universal Windows Application Launcher — Zye Day 16 & Day 36 Reliability Upgrade.
Launches Win32, Store (UWP), and desktop applications with multi-backend window verification,
ambiguity resolution, and strict zero-false-success enforcement.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from typing import Any, Dict, Optional

from zye_windows.app_discovery import WindowsAppDiscovery
from zye_windows.application_execution_schema import (
    ApplicationExecutionResult,
    ApplicationExecutionStatus,
)
from zye_windows.application_resolver import ApplicationResolver
from zye_windows.window_manager import WindowsWindowManager
from zye_windows.window_verifier import WindowVerifier
from zye_windows.windows_models import AppInfo, InstallationType

logger = logging.getLogger("zye.windows.app_launcher")

DEFAULT_LAUNCH_TIMEOUT_SECONDS = 15.0


class WindowsAppLauncher:
    """
    Launches discoverable Windows applications safely using verified AppIDs or executables,
    strictly validating actual window emergence before reporting success.
    """

    def __init__(
        self,
        discovery: Optional[WindowsAppDiscovery] = None,
        window_mgr: Optional[WindowsWindowManager] = None,
        default_timeout: float = DEFAULT_LAUNCH_TIMEOUT_SECONDS,
    ) -> None:
        self.discovery = discovery or WindowsAppDiscovery()
        self.window_mgr = window_mgr or WindowsWindowManager()
        self.default_timeout = default_timeout
        self.resolver = ApplicationResolver(discovery=self.discovery)

    def open_any_app(self, app_name: str, timeout: Optional[float] = None) -> dict[str, Any]:
        """
        Open a Windows application by common name or AppID.
        Checks if already running, launches, and verifies responsive window emergence.
        Zero false success: returns verified=True ONLY if a top-level window appeared.
        """
        start_ts = time.monotonic()
        if not app_name or not str(app_name).strip():
            res = ApplicationExecutionResult(
                status=ApplicationExecutionStatus.APP_NOT_FOUND,
                requested_application=str(app_name or ""),
                resolved_application="unknown",
                verified=False,
                message="Application name cannot be empty.",
                error="Empty application name provided.",
            )
            return res.model_dump()

        effective_timeout = timeout if timeout is not None else self.default_timeout
        clean_name = str(app_name).strip()

        # 1. Resolve application with alias and ambiguity protection
        resolve_status, target_app, candidates = self.resolver.resolve(clean_name)

        if resolve_status == "AMBIGUOUS_MATCH":
            res = ApplicationExecutionResult(
                status=ApplicationExecutionStatus.AMBIGUOUS_APP_MATCH,
                requested_application=clean_name,
                resolved_application=clean_name,
                verified=False,
                candidates=candidates,
                message=f"Multiple applications match '{clean_name}'. Please specify which one.",
            )
            return res.model_dump()

        if resolve_status == "NOT_FOUND" or target_app is None:
            res = ApplicationExecutionResult(
                status=ApplicationExecutionStatus.APP_NOT_FOUND,
                requested_application=clean_name,
                resolved_application=clean_name,
                verified=False,
                message=f"Application '{clean_name}' could not be found among registered applications.",
            )
            return res.model_dump()

        # 2. Check if a window for this application is ALREADY OPEN
        existing_win = WindowVerifier.verify_window(
            app_name=target_app.application_name,
            app_id=target_app.app_id,
            executable_name=target_app.executable_path,
        )

        if existing_win.get("found"):
            # Focus existing window
            try:
                self.window_mgr.manage_window(target_app.application_name, "focus")
            except Exception:
                pass

            elapsed_ms = round((time.monotonic() - start_ts) * 1000, 2)
            res = ApplicationExecutionResult(
                status=ApplicationExecutionStatus.ALREADY_OPEN,
                requested_application=clean_name,
                resolved_application=target_app.application_name,
                appid=target_app.app_id,
                process_id=existing_win.get("pid"),
                window_title=existing_win.get("title"),
                hwnd=existing_win.get("hwnd"),
                window_visible=True,
                uia_accessible=existing_win.get("uia_accessible", True),
                launch_method="ALREADY_ACTIVE",
                verification_method=existing_win.get("verification_method", "WIN32_MATCH"),
                execution_time_ms=elapsed_ms,
                verified=True,
                message=f"Application '{target_app.application_name}' is already open and verified active.",
            )
            return res.model_dump()

        # 3. Launch application process
        launch_ok, launch_method, launch_err = self._launch_app_process(target_app)
        if not launch_ok:
            elapsed_ms = round((time.monotonic() - start_ts) * 1000, 2)
            res = ApplicationExecutionResult(
                status=ApplicationExecutionStatus.LAUNCH_FAILED,
                requested_application=clean_name,
                resolved_application=target_app.application_name,
                appid=target_app.app_id,
                verified=False,
                launch_method=launch_method,
                execution_time_ms=elapsed_ms,
                message=f"Failed to launch '{target_app.application_name}': {launch_err}",
                error=str(launch_err),
            )
            return res.model_dump()

        # 4. Multi-backend Verification Polling: wait for actual window to emerge
        poll_interval = 0.4
        verified_win: Dict[str, Any] = {}

        while (time.monotonic() - start_ts) < effective_timeout:
            time.sleep(poll_interval)
            win_check = WindowVerifier.verify_window(
                app_name=target_app.application_name,
                app_id=target_app.app_id,
                executable_name=target_app.executable_path,
            )
            if win_check.get("found"):
                verified_win = win_check
                break

        elapsed_ms = round((time.monotonic() - start_ts) * 1000, 2)

        # 5. Formulate strictly verified result
        if verified_win.get("found"):
            # Focus newly emerged window
            try:
                self.window_mgr.manage_window(target_app.application_name, "focus")
            except Exception:
                pass

            res = ApplicationExecutionResult(
                status=ApplicationExecutionStatus.UI_READY,
                requested_application=clean_name,
                resolved_application=target_app.application_name,
                appid=target_app.app_id,
                process_id=verified_win.get("pid"),
                window_title=verified_win.get("title"),
                hwnd=verified_win.get("hwnd"),
                window_visible=True,
                uia_accessible=verified_win.get("uia_accessible", True),
                launch_method=launch_method,
                verification_method=verified_win.get("verification_method", "WINDOW_AND_UIA"),
                execution_time_ms=elapsed_ms,
                verified=True,
                message=f"Application '{target_app.application_name}' successfully opened and verified on desktop.",
            )
            return res.model_dump()
        else:
            # Process was dispatched, but no visible window confirmed before timeout
            res = ApplicationExecutionResult(
                status=ApplicationExecutionStatus.WINDOW_TIMEOUT,
                requested_application=clean_name,
                resolved_application=target_app.application_name,
                appid=target_app.app_id,
                verified=False,
                launch_method=launch_method,
                verification_method="NONE",
                execution_time_ms=elapsed_ms,
                message=f"Launch request was submitted, but the application window for '{target_app.application_name}' did not appear within {effective_timeout}s.",
            )
            return res.model_dump()

    def _launch_app_process(self, app: AppInfo) -> tuple[bool, str, str]:
        """
        Launch application process via direct executable, App Paths, or explorer shell:AppsFolder.
        Returns:
            (success_bool, launch_method_string, error_message)
        """
        if sys.platform != "win32":
            return False, "UNKNOWN", "Non-Windows platform not supported"

        app_id = app.app_id
        try:
            # 1. Direct executable path if present and valid
            if app.executable_path and os.path.exists(app.executable_path):
                os.startfile(app.executable_path)
                return True, "DIRECT_EXECUTABLE", ""

            # 2. Known standard Windows executables via App Paths
            norm = app.application_name.lower().strip()
            exe_map = {
                "google chrome": "chrome.exe",
                "chrome": "chrome.exe",
                "notepad": "notepad.exe",
                "calculator": "calc.exe",
                "microsoft word": "winword.exe",
                "word": "winword.exe",
                "microsoft excel": "excel.exe",
                "excel": "excel.exe",
                "microsoft powerpoint": "powerpnt.exe",
                "powerpoint": "powerpnt.exe",
                "outlook": "outlook.exe",
                "microsoft edge": "msedge.exe",
                "edge": "msedge.exe",
                "file explorer": "explorer.exe",
            }
            if norm in exe_map:
                try:
                    os.startfile(exe_map[norm])
                    return True, "APP_PATHS", ""
                except Exception as ex_direct:
                    logger.debug("Direct launch of %s failed: %s; trying AppID", exe_map[norm], ex_direct)

            # 3. Store / UWP App or registered Start Menu app with AppID
            if app_id:
                cmd = ["explorer.exe", f"shell:AppsFolder\\{app_id}"]
                subprocess.Popen(cmd)
                return True, "START_MENU_APPMODEL", ""

            # 4. Fallback: try os.startfile on application name
            os.startfile(app.application_name)
            return True, "DEFAULT_SHELL_HANDLER", ""
        except Exception as exc:
            logger.error("Failed to execute launch for '%s': %s", app.application_name, exc)
            return False, "FAILED", str(exc)
