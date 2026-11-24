"""
Persistent Browser Profile Registry — Day 24.
Maintains profile catalog, aliases, tags, Tamil mappings, and usage timestamps.
"""

from __future__ import annotations

import datetime
import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from zye_browser.browser_errors import BrowserProfileNotFoundError
from zye_browser.models import BrowserProfileMetadata, DiscoveredChromeProfile
from zye_browser.profile_path_validator import ProfilePathValidator

logger = logging.getLogger("ZyeBrowserRegistry")


class ProfileRegistry:
    """Stores and synchronizes persistent browser profile records for Zye."""

    def __init__(self, registry_file: Optional[Path] = None, profiles_root: Optional[Path] = None) -> None:
        self.profiles_root = profiles_root or ProfilePathValidator.get_default_profiles_root()
        self.registry_file = registry_file or (self.profiles_root / "registry.json")
        self._profiles: Dict[str, BrowserProfileMetadata] = {}
        self._active_profile_id: Optional[str] = None
        self._load()

    def _load(self) -> None:
        """Load registry from JSON file or create initial empty state."""
        if not self.registry_file.exists():
            self._profiles = {}
            return

        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._profiles = {
                pid: BrowserProfileMetadata(**p_data)
                for pid, p_data in data.get("profiles", {}).items()
            }
            self._active_profile_id = data.get("active_profile_id")
        except Exception as exc:
            logger.error("Failed to load browser profile registry: %s", exc)
            self._profiles = {}

    def _save(self) -> None:
        """Serialize current profile registry state to JSON atomically."""
        try:
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "version": "1.0",
                "last_updated": datetime.datetime.now().isoformat(),
                "active_profile_id": self._active_profile_id,
                "profiles": {pid: p.model_dump() for pid, p in self._profiles.items()},
            }
            temp_file = self.registry_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.registry_file)
        except Exception as exc:
            logger.error("Failed to save browser profile registry: %s", exc)

    def register_profile(
        self,
        profile_id: str,
        display_name: str,
        email: Optional[str] = None,
        account_type: str = "google",
        aliases: Optional[List[str]] = None,
        tamil_aliases: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> BrowserProfileMetadata:
        """Create or register a persistent profile."""
        clean_id = ProfilePathValidator.validate_profile_id(profile_id)
        user_data_dir = str(ProfilePathValidator.ensure_profile_dir(clean_id, self.profiles_root))

        profile = BrowserProfileMetadata(
            profile_id=clean_id,
            display_name=display_name.strip(),
            email=email.strip() if email else None,
            account_type=account_type,
            user_data_dir=user_data_dir,
            aliases=aliases or [],
            tamil_aliases=tamil_aliases or [],
            tags=tags or [],
            notes=notes,
        )

        self._profiles[clean_id] = profile
        self._save()
        return profile

    def get_profile(self, profile_id: str) -> Optional[BrowserProfileMetadata]:
        """Retrieve profile by ID."""
        clean_id = profile_id.strip()
        return self._profiles.get(clean_id)

    def list_profiles(self) -> List[BrowserProfileMetadata]:
        """Return list of all registered profiles."""
        return list(self._profiles.values())

    def update_profile(self, profile_id: str, **kwargs: Any) -> BrowserProfileMetadata:
        """Update metadata fields of an existing profile."""
        profile = self.get_profile(profile_id)
        if not profile:
            raise BrowserProfileNotFoundError(
                code="ERR_BROWSER_PROFILE_NOT_FOUND",
                message=f"Browser profile '{profile_id}' is not registered.",
                profile_id=profile_id,
                remediation="Register the profile first or run profile discovery.",
            )

        updated_dict = profile.model_dump()
        for k, v in kwargs.items():
            if k in updated_dict and v is not None:
                updated_dict[k] = v

        updated_profile = BrowserProfileMetadata(**updated_dict)
        self._profiles[profile.profile_id] = updated_profile
        self._save()
        return updated_profile

    def delete_profile(self, profile_id: str, delete_files: bool = False) -> bool:
        """Remove profile from registry, optionally deleting on-disk user data directory."""
        clean_id = profile_id.strip()
        if clean_id not in self._profiles:
            return False

        profile = self._profiles.pop(clean_id)
        if self._active_profile_id == clean_id:
            self._active_profile_id = None

        if delete_files and profile.user_data_dir:
            path = Path(profile.user_data_dir)
            if path.exists():
                try:
                    shutil.rmtree(path, ignore_errors=True)
                except Exception as exc:
                    logger.warning("Could not delete profile directory %s: %s", path, exc)

        self._save()
        return True

    def get_active_profile(self) -> Optional[BrowserProfileMetadata]:
        """Return currently active profile if any."""
        if self._active_profile_id:
            return self._profiles.get(self._active_profile_id)
        return None

    def set_active_profile(self, profile_id: Optional[str]) -> None:
        """Set or clear active profile ID."""
        if profile_id and profile_id not in self._profiles:
            raise BrowserProfileNotFoundError(
                code="ERR_BROWSER_PROFILE_NOT_FOUND",
                message=f"Cannot activate non-existent profile '{profile_id}'.",
                profile_id=profile_id,
            )
        self._active_profile_id = profile_id
        for pid, p in self._profiles.items():
            p.is_active = (pid == profile_id)
        self._save()

    def sync_from_host_chrome(self, discovered_profiles: List[DiscoveredChromeProfile]) -> List[BrowserProfileMetadata]:
        """
        Auto-populate registry from discovered host Chrome profiles if not already present.
        Assigns standard aliases and Tamil keywords.
        """
        added: List[BrowserProfileMetadata] = []
        for disc in discovered_profiles:
            # Generate safe ID: e.g. "default", "profile_13", or derived from name/email
            raw_id = disc.chrome_profile_dir.lower().replace(" ", "_")
            if raw_id in self._profiles:
                continue

            # Derive aliases based on name and email
            aliases = [disc.name.lower(), disc.chrome_profile_dir.lower()]
            tamil_aliases: List[str] = []

            # Add intelligent tags
            tags = ["chrome_import"]
            if disc.email:
                local_part = disc.email.split("@")[0].lower()
                aliases.append(local_part)
                if "work" in disc.email.lower() or "office" in disc.name.lower():
                    tags.append("work")
                    aliases.extend(["work", "office"])
                    tamil_aliases.extend(["வேலை", "ஆபீஸ்", "work account"])
                elif "zyren" in disc.name.lower() or "zyren" in disc.email.lower():
                    tags.append("zyren")
                    aliases.extend(["zyren", "bot"])
                    tamil_aliases.extend(["சைரன்", "zyren"])
                else:
                    tags.append("personal")
                    aliases.append("personal")
                    tamil_aliases.extend(["சொந்தம்", "personal account"])

            user_dir = str(ProfilePathValidator.ensure_profile_dir(raw_id, self.profiles_root))
            meta = BrowserProfileMetadata(
                profile_id=raw_id,
                display_name=disc.name,
                email=disc.email,
                account_type="google",
                user_data_dir=user_dir,
                aliases=list(set(aliases)),
                tamil_aliases=list(set(tamil_aliases)),
                tags=tags,
                notes=f"Imported metadata from Chrome {disc.chrome_profile_dir}",
            )
            self._profiles[raw_id] = meta
            added.append(meta)

        if added:
            self._save()
        return added
