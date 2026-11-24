"""
Path Validation for Persistent Browser Profiles — Day 24.
Prevents directory traversal, path injection, and verifies safe storage locations.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from zye_browser.browser_errors import BrowserProfileError

# Safe alphanumeric + underscore + hyphen identifier
SAFE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")


class ProfilePathValidator:
    """Validates profile directories and identifiers to guarantee security isolation."""

    @staticmethod
    def get_default_profiles_root() -> Path:
        """Resolve default persistent profiles root directory under %LOCALAPPDATA%\\ZyeAI\\browser_profiles with local fallback."""
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidate = Path(local_app_data) / "ZyeAI" / "browser_profiles"
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                test_f = candidate / ".perm_check"
                test_f.write_text("ok", encoding="utf-8")
                test_f.unlink(missing_ok=True)
                return candidate.resolve()
            except Exception:
                pass

        # Fallback to workspace data directory
        workspace_base = Path.cwd() / "data" / "browser_profiles"
        try:
            workspace_base.mkdir(parents=True, exist_ok=True)
            return workspace_base.resolve()
        except Exception:
            return (Path.home() / ".zye" / "browser_profiles").resolve()

    @staticmethod
    def validate_profile_id(profile_id: str) -> str:
        """
        Validate profile identifier string.
        Must be 1-64 chars, containing only alphanumeric, underscore, or hyphen characters.
        """
        if not profile_id or not isinstance(profile_id, str):
            raise BrowserProfileError(
                code="ERR_BROWSER_PROFILE_INVALID_ID",
                message="Profile ID cannot be empty and must be a valid string.",
                profile_id=str(profile_id),
                remediation="Provide an alphanumeric profile identifier (e.g. 'work', 'personal', 'profile_1').",
            )

        clean_id = profile_id.strip()
        if not (1 <= len(clean_id) <= 64):
            raise BrowserProfileError(
                code="ERR_BROWSER_PROFILE_INVALID_LENGTH",
                message=f"Profile ID '{clean_id}' length ({len(clean_id)}) must be between 1 and 64 characters.",
                profile_id=clean_id,
            )

        if not SAFE_ID_REGEX.match(clean_id):
            raise BrowserProfileError(
                code="ERR_BROWSER_PROFILE_UNSAFE_CHARS",
                message=f"Profile ID '{clean_id}' contains invalid characters. Only letters, digits, _, and - allowed.",
                profile_id=clean_id,
                remediation="Ensure profile ID matches regex: ^[a-zA-Z0-9_\\-]+$",
            )

        return clean_id

    @classmethod
    def resolve_profile_dir(cls, profile_id: str, base_root: Optional[Path] = None) -> Path:
        """
        Safely resolve profile directory path and ensure no directory traversal occurs.
        Creates parent directories if necessary.
        """
        clean_id = cls.validate_profile_id(profile_id)
        root = (base_root or cls.get_default_profiles_root()).resolve()

        target = (root / f"profile_{clean_id}").resolve()

        # Security check: ensure target is strictly inside root
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise BrowserProfileError(
                code="ERR_BROWSER_PATH_TRAVERSAL",
                message=f"Attempted directory traversal detected for profile ID '{profile_id}'.",
                profile_id=clean_id,
                remediation="Use a plain identifier without slashes or traversal sequences.",
            ) from exc

        return target

    @classmethod
    def ensure_profile_dir(cls, profile_id: str, base_root: Optional[Path] = None) -> Path:
        """Ensure profile directory exists with safe permissions and return Path."""
        profile_path = cls.resolve_profile_dir(profile_id, base_root)
        profile_path.mkdir(parents=True, exist_ok=True)
        return profile_path
