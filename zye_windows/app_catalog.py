"""
Universal Windows Application Catalog — Zye Day 19.
Unified discovery, search, launch target resolution, and launch verification for Win32, Store (UWP),
and registered desktop applications with atomic JSON caching in data/windows_app_cache.json.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import sys
import time
from typing import Any, Optional

from zye_windows.app_discovery import WindowsAppDiscovery
from zye_windows.app_launcher import WindowsAppLauncher
from zye_windows.window_manager import WindowsWindowManager
from zye_windows.windows_models import AppInfo, InstallationType

logger = logging.getLogger("zye.windows.app_catalog")

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"
APP_CACHE_FILE = DATA_DIR / "windows_app_cache.json"


def normalize_voice_app_name(name: str) -> str:
    """Normalizes colloquial and multilingual app names to canonical executable or key."""
    norm = name.strip().lower()
    mapping = {
        "word": "winword",
        "ms word": "winword",
        "microsoft word": "winword",
        "excel": "excel",
        "ms excel": "excel",
        "powerpoint": "powerpnt",
        "ms powerpoint": "powerpnt",
        "ppt": "powerpnt",
        "outlook": "outlook",
        "ms outlook": "outlook",
        "chrome": "chrome",
        "google chrome": "chrome",
        "notepad": "notepad",
        "whatsapp": "whatsapp",
    }
    return mapping.get(norm, norm)


class WindowsAppCatalog:
    """
    Unified Application Catalog providing discovery, search, launch target resolution,
    and post-launch verification across all installed Windows applications.
    """

    def __init__(
        self,
        cache_file: Optional[pathlib.Path] = None,
        discovery: Optional[WindowsAppDiscovery] = None,
        launcher: Optional[WindowsAppLauncher] = None,
        window_mgr: Optional[WindowsWindowManager] = None,
    ) -> None:
        self.cache_file = cache_file or APP_CACHE_FILE
        self.discovery = discovery or WindowsAppDiscovery(cache_file=self.cache_file)
        self.window_mgr = window_mgr or WindowsWindowManager()
        self.launcher = launcher or WindowsAppLauncher(
            discovery=self.discovery,
            window_mgr=self.window_mgr,
        )

    def discover_installed_apps(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """
        Discover all installed applications on the Windows system.
        Returns serialized list of application descriptors.
        """
        apps = self.discovery.get_installed_apps(force_refresh=force_refresh)
        return [
            {
                "name": a.application_name,
                "app_id": a.app_id,
                "type": a.installation_type.value if hasattr(a.installation_type, "value") else str(a.installation_type),
                "available": a.available,
                "executable_path": a.executable_path,
                "launch_target": getattr(a, "launch_target", None) or a.app_id,
            }
            for a in apps
        ]

    def search_installed_apps(self, query: str) -> list[dict[str, Any]]:
        """
        Search for applications matching query string (case-insensitive fuzzy or substring).
        """
        if not query or not str(query).strip():
            return []
        matches = self.discovery.search_installed_apps(str(query).strip())
        return [
            {
                "name": m.application_name,
                "app_id": m.app_id,
                "type": m.installation_type.value if hasattr(m.installation_type, "value") else str(m.installation_type),
                "available": m.available,
                "executable_path": m.executable_path,
                "launch_target": getattr(m, "launch_target", None) or m.app_id,
            }
            for m in matches
        ]

    def get_application_details(self, app_id_or_name: str) -> dict[str, Any]:
        """
        Fetch exhaustive details for an application identified by name or AppID.
        """
        if not app_id_or_name or not str(app_id_or_name).strip():
            return {"status": "ERROR", "message": "Application identifier cannot be empty."}

        target = str(app_id_or_name).strip()
        all_apps = self.discovery.get_installed_apps()

        # Try exact app_id match first
        for a in all_apps:
            if a.app_id.lower() == target.lower():
                return {
                    "status": "SUCCESS",
                    "application": a.application_name,
                    "app_id": a.app_id,
                    "type": a.installation_type.value if hasattr(a.installation_type, "value") else str(a.installation_type),
                    "executable_path": a.executable_path,
                    "launch_target": getattr(a, "launch_target", None) or a.app_id,
                    "available": a.available,
                }

        # Try name match
        matches = [a for a in all_apps if target.lower() in a.application_name.lower()]
        if len(matches) == 1:
            a = matches[0]
            return {
                "status": "SUCCESS",
                "application": a.application_name,
                "app_id": a.app_id,
                "type": a.installation_type.value if hasattr(a.installation_type, "value") else str(a.installation_type),
                "executable_path": a.executable_path,
                "launch_target": getattr(a, "launch_target", None) or a.app_id,
                "available": a.available,
            }
        elif len(matches) > 1:
            return {
                "status": "AMBIGUOUS_MATCH",
                "message": f"Multiple applications match '{target}'. Specify exact app_id.",
                "candidates": [f"{m.application_name} ({m.app_id})" for m in matches[:5]],
            }

        return {
            "status": "NOT_FOUND",
            "message": f"Application '{target}' not found in installed catalog.",
            "app_id_or_name": target,
        }

    def get_application_launch_target(self, app_id_or_name: str) -> dict[str, Any]:
        """Resolve launch target (executable or Store AppsFolder URI) for application."""
        details = self.get_application_details(app_id_or_name)
        if details.get("status") != "SUCCESS":
            return details

        app_type = details.get("type", "UNKNOWN")
        app_id = details.get("app_id", "")
        exe = details.get("executable_path")

        if app_type == "STORE":
            launch_str = f"shell:AppsFolder\\{app_id}"
            return {
                "status": "SUCCESS",
                "application": details.get("application"),
                "app_id": app_id,
                "launch_target": launch_str,
                "method": "EXPLORER_URI",
            }
        else:
            launch_str = exe or app_id
            return {
                "status": "SUCCESS",
                "application": details.get("application"),
                "app_id": app_id,
                "launch_target": launch_str,
                "method": "PROCESS_SPAWN",
            }

    def launch_application(self, app_name_or_id: str, timeout: float = 15.0) -> dict[str, Any]:
        """
        Safely launch an application and wait for responsive window emergence.
        """
        return self.launcher.open_any_app(app_name_or_id, timeout=timeout)

    def verify_application_launch(self, app_name_or_id: str, timeout: float = 10.0) -> dict[str, Any]:
        """
        Verify whether an application is running with an active or discoverable top-level window.
        """
        if not app_name_or_id or not str(app_name_or_id).strip():
            return {"status": "ERROR", "message": "Identifier cannot be empty."}

        target = str(app_name_or_id).strip()
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            wins = self.window_mgr.find_windows(target)
            if wins:
                w = wins[0]
                return {
                    "status": "VERIFIED",
                    "application": target,
                    "window_title": getattr(w, "title", target),
                    "hwnd": getattr(w, "_hWnd", 0),
                    "is_running": True,
                }
            time.sleep(0.5)

        return {
            "status": "UNVERIFIED",
            "application": target,
            "is_running": False,
            "message": f"No active window detected for '{target}' within {timeout}s timeout.",
        }
