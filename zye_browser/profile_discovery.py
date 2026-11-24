"""
Chrome Profile Discovery Module — Day 24.
Discovers host Chrome profiles and accounts via Local State metadata without accessing credentials or private tokens.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import List, Optional

from zye_browser.models import DiscoveredChromeProfile

logger = logging.getLogger("ZyeBrowserDiscovery")


class ChromeProfileDiscovery:
    """Safely discovers installed Google Chrome profiles on Windows hosts."""

    @staticmethod
    def get_chrome_user_data_dir() -> Optional[Path]:
        """Locate Google Chrome's User Data directory on Windows."""
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            return None

        candidates = [
            Path(local_app_data) / "Google" / "Chrome" / "User Data",
            Path(local_app_data) / "Google" / "Chrome Beta" / "User Data",
            Path(local_app_data) / "Google" / "Chrome Dev" / "User Data",
            Path(local_app_data) / "Chromium" / "User Data",
        ]

        for p in candidates:
            if p.exists() and (p / "Local State").exists():
                return p

        # Default fallback even if Local State not yet found
        default_dir = Path(local_app_data) / "Google" / "Chrome" / "User Data"
        if default_dir.exists():
            return default_dir

        return None

    @classmethod
    def discover_chrome_profiles(cls, user_data_dir: Optional[Path] = None) -> List[DiscoveredChromeProfile]:
        """
        Parse host Chrome's Local State file and extract non-sensitive metadata for all profiles.
        NEVER reads or extracts passwords, cookies, or encryption keys.
        """
        data_dir = user_data_dir or cls.get_chrome_user_data_dir()
        if not data_dir or not data_dir.exists():
            logger.info("Chrome User Data directory not found or inaccessible.")
            return []

        local_state_file = data_dir / "Local State"
        if not local_state_file.exists():
            logger.info("Chrome Local State file not found at %s", local_state_file)
            return []

        discovered: List[DiscoveredChromeProfile] = []
        try:
            with open(local_state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)

            profile_info_cache = state_data.get("profile", {}).get("info_cache", {})

            for dir_name, info in profile_info_cache.items():
                name = info.get("name") or dir_name
                email = info.get("user_name") or None
                # If user_name is not an email, check if gaia_name or hosted_domain exists
                gaia_name = info.get("gaia_name") or None
                avatar_icon = info.get("avatar_icon") or None
                is_ephemeral = bool(info.get("is_ephemeral", False))
                raw_path = str(data_dir / dir_name)

                # Clean email string if empty
                if email and "@" not in email:
                    # Sometimes user_name is a display name or empty
                    email = None

                item = DiscoveredChromeProfile(
                    chrome_profile_dir=dir_name,
                    name=name,
                    email=email,
                    gaia_name=gaia_name,
                    avatar_icon=avatar_icon,
                    is_ephemeral=is_ephemeral,
                    raw_data_path=raw_path,
                )
                discovered.append(item)

        except Exception as exc:
            logger.error("Failed to parse Chrome Local State: %s", exc)

        return discovered

    @classmethod
    def get_host_chrome_executable(cls) -> Optional[Path]:
        """Find the 64-bit or 32-bit Chrome binary path on Windows."""
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app_data = os.environ.get("LOCALAPPDATA", "")

        candidates = [
            Path(program_files) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(program_files_x86) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(local_app_data) / "Google" / "Chrome" / "Application" / "chrome.exe",
        ]

        for p in candidates:
            if p.exists():
                return p

        return None
