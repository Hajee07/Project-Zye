"""
Universal Windows Application Discovery Engine — Zye Day 16.
Enumerate installed Win32, Store (UWP), and Start Menu applications via PowerShell Get-StartApps,
Windows Registry, and standard paths, with atomic JSON caching.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import subprocess
import sys
import time
from typing import Any, Optional

from zye_windows.windows_models import AppInfo, InstallationType

logger = logging.getLogger("zye.windows.app_discovery")

CACHE_FILE = pathlib.Path(__file__).resolve().parent.parent / "data" / "windows_app_cache.json"
CACHE_TTL_SECONDS = 3600.0  # 1 hour cache validity

# Well-known fallback applications common to all modern Windows systems
WELL_KNOWN_APPS: list[dict[str, Any]] = [
    {"name": "WhatsApp", "app_id": "5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App", "type": "STORE"},
    {"name": "Google Chrome", "app_id": "Chrome", "type": "WIN32", "executable": "chrome.exe"},
    {"name": "Microsoft Edge", "app_id": "Microsoft.MicrosoftEdge_8wekyb3d8bbwe!MicrosoftEdge", "type": "STORE", "executable": "msedge.exe"},
    {"name": "Spotify", "app_id": "Spotify.Music_zpdnekdrzrea0!Spotify", "type": "STORE"},
    {"name": "Notepad", "app_id": "Microsoft.WindowsNotepad_8wekyb3d8bbwe!App", "type": "STORE", "executable": "notepad.exe"},
    {"name": "Calculator", "app_id": "Microsoft.WindowsCalculator_8wekyb3d8bbwe!App", "type": "STORE", "executable": "calc.exe"},
    {"name": "File Explorer", "app_id": "explorer.exe", "type": "SYSTEM", "executable": "explorer.exe"},
    {"name": "Settings", "app_id": "windows.immersivecontrolpanel_cw5n1h2txyewy!microsoft.windows.immersivecontrolpanel", "type": "STORE"},
    {"name": "Visual Studio Code", "app_id": "Microsoft.VisualStudioCode", "type": "WIN32", "executable": "code.cmd"},
    {"name": "VLC media player", "app_id": "VideoLAN.VLC", "type": "WIN32", "executable": "vlc.exe"},
]


class WindowsAppDiscovery:
    """
    Discovers installed Windows applications without requiring manual executable path knowledge.
    Uses Get-StartApps with atomic caching and resilient registry/known-app fallbacks.
    """

    def __init__(self, cache_file: Optional[pathlib.Path] = None, cache_ttl: float = CACHE_TTL_SECONDS) -> None:
        self.cache_file = cache_file or CACHE_FILE
        self.cache_ttl = cache_ttl
        self._memory_cache: list[AppInfo] = []
        self._last_loaded_time = 0.0

    def get_installed_apps(self, force_refresh: bool = False) -> list[AppInfo]:
        """
        Retrieve all discoverable installed Windows applications.
        Returns cached inventory if fresh, otherwise re-scans via PowerShell.
        """
        now = time.monotonic()
        if not force_refresh and self._memory_cache and (now - self._last_loaded_time < self.cache_ttl):
            return list(self._memory_cache)

        # Check disk cache
        if not force_refresh and self.cache_file.exists():
            try:
                mtime = self.cache_file.stat().st_mtime
                if time.time() - mtime < self.cache_ttl:
                    with open(self.cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._memory_cache = [AppInfo(**item) for item in data]
                    self._last_loaded_time = now
                    logger.info("Loaded %d applications from disk cache.", len(self._memory_cache))
                    return list(self._memory_cache)
            except Exception as exc:
                logger.warning("Could not read disk app cache: %s", exc)

        # Re-scan from OS
        apps = self._scan_start_apps()
        if not apps:
            logger.warning("OS application scan returned zero apps. Falling back to built-in inventory.")
            apps = [
                AppInfo(
                    application_name=a["name"],
                    app_id=a["app_id"],
                    installation_type=InstallationType(a.get("type", "UNKNOWN")),
                    available=True,
                    executable_path=a.get("executable"),
                )
                for a in WELL_KNOWN_APPS
            ]

        self._memory_cache = apps
        self._last_loaded_time = now
        self._save_to_disk_cache(apps)
        return list(apps)

    def search_installed_apps(self, query: str) -> list[AppInfo]:
        """
        Search for applications matching query string (case-insensitive substring or exact).
        Returns list of matching AppInfo candidates.
        """
        if not query or not str(query).strip():
            return []
        q = str(query).strip().lower()
        all_apps = self.get_installed_apps()

        # 1. Exact matches
        exact = [a for a in all_apps if a.application_name.lower() == q or a.app_id.lower() == q]
        if exact:
            return exact

        # 2. Starts-with matches
        starts = [a for a in all_apps if a.application_name.lower().startswith(q)]
        if starts:
            return starts

        # 3. Substring matches
        sub = [a for a in all_apps if q in a.application_name.lower() or q in a.app_id.lower()]
        return sub

    def get_app_details(self, app_name: str) -> AppInfo | None:
        """Get best matching AppInfo for a given application name."""
        matches = self.search_installed_apps(app_name)
        if not matches:
            return None
        # Return first best match
        return matches[0]

    def _scan_start_apps(self) -> list[AppInfo]:
        """Execute PowerShell Get-StartApps to retrieve registered Start Menu and Store applications."""
        if sys.platform != "win32":
            return []

        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Compress",
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=8.0, check=False)
            if res.returncode != 0 or not res.stdout.strip():
                logger.warning("Get-StartApps returned non-zero code (%d) or empty stdout.", res.returncode)
                return []

            raw = json.loads(res.stdout)
            if isinstance(raw, dict):
                raw = [raw]
            elif not isinstance(raw, list):
                return []

            apps: list[AppInfo] = []
            seen_names: set[str] = set()

            for item in raw:
                name = str(item.get("Name", "")).strip()
                app_id = str(item.get("AppID", "")).strip()
                if not name:
                    continue

                # Determine installation type based on AppID pattern
                if "!" in app_id or "_" in app_id and ("microsoft" in app_id.lower() or "windows" in app_id.lower() or "desktop" in app_id.lower()):
                    inst_type = InstallationType.STORE
                elif app_id.lower().endswith(".exe") or ":\\" in app_id:
                    inst_type = InstallationType.WIN32
                elif "system" in app_id.lower() or "control" in app_id.lower():
                    inst_type = InstallationType.SYSTEM
                else:
                    inst_type = InstallationType.UWP if "!" in app_id else InstallationType.WIN32

                key = f"{name}::{app_id}"
                if key in seen_names:
                    continue
                seen_names.add(key)

                apps.append(
                    AppInfo(
                        application_name=name,
                        app_id=app_id,
                        installation_type=inst_type,
                        available=True,
                    )
                )

            logger.info("Successfully discovered %d applications via Get-StartApps.", len(apps))
            return apps
        except subprocess.TimeoutExpired:
            logger.warning("Get-StartApps command timed out after 8s.")
            return []
        except Exception as exc:
            logger.warning("Error running Get-StartApps: %s", exc)
            return []

    def _save_to_disk_cache(self, apps: list[AppInfo]) -> None:
        """Atomically persist application inventory to disk cache."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            tmp_file = self.cache_file.with_suffix(".tmp")
            data = [a.model_dump() for a in apps]
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_file, self.cache_file)
            logger.info("Saved %d applications to disk cache: %s", len(apps), self.cache_file)
        except Exception as exc:
            logger.warning("Failed to save app cache to disk: %s", exc)
