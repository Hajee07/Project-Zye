"""
Profile Manager Orchestrator — Day 24.
Coordinates discovery, validation, locking, persistence, and account disambiguation for persistent browser profiles.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from zye_browser.account_selector import AccountSelector
from zye_browser.browser_errors import (
    BrowserProfileLockedError,
    BrowserProfileNotFoundError,
)
from zye_browser.models import (
    BrowserAccountSelection,
    BrowserProfileMetadata,
    DiscoveredChromeProfile,
)
from zye_browser.profile_discovery import ChromeProfileDiscovery
from zye_browser.profile_lock_manager import ProfileLockManager
from zye_browser.profile_path_validator import ProfilePathValidator
from zye_browser.profile_registry import ProfileRegistry

logger = logging.getLogger("ZyeBrowserProfileManager")


class ProfileManager:
    """Central manager for persistent browser profiles, synchronization, and safe locks."""

    def __init__(
        self,
        profiles_root: Optional[Path] = None,
        registry_file: Optional[Path] = None,
    ) -> None:
        self.profiles_root = profiles_root or ProfilePathValidator.get_default_profiles_root()
        self.registry = ProfileRegistry(registry_file=registry_file, profiles_root=self.profiles_root)
        self.selector = AccountSelector(self.registry)
        self.lock_manager = ProfileLockManager()

    def discover_host_profiles(self) -> List[DiscoveredChromeProfile]:
        """Discover profiles from host Google Chrome installation."""
        return ChromeProfileDiscovery.discover_chrome_profiles()

    def sync_from_host(self) -> List[BrowserProfileMetadata]:
        """Auto-import host Chrome profiles into Zye profile registry."""
        discovered = self.discover_host_profiles()
        return self.registry.sync_from_host_chrome(discovered)

    def list_profiles(self) -> List[BrowserProfileMetadata]:
        """List all registered persistent profiles, updating lock status."""
        profiles = self.registry.list_profiles()
        for p in profiles:
            p_dir = Path(p.user_data_dir)
            p.is_locked = self.lock_manager.is_profile_locked(p_dir)
        return profiles

    def get_profile(self, profile_id: str) -> Optional[BrowserProfileMetadata]:
        """Get profile by ID."""
        p = self.registry.get_profile(profile_id)
        if p:
            p.is_locked = self.lock_manager.is_profile_locked(Path(p.user_data_dir))
        return p

    def create_profile(
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
        """Create and register a new persistent profile."""
        return self.registry.register_profile(
            profile_id=profile_id,
            display_name=display_name,
            email=email,
            account_type=account_type,
            aliases=aliases,
            tamil_aliases=tamil_aliases,
            tags=tags,
            notes=notes,
        )

    def update_profile(self, profile_id: str, **kwargs: Any) -> BrowserProfileMetadata:
        """Update existing profile metadata."""
        return self.registry.update_profile(profile_id, **kwargs)

    def delete_profile(self, profile_id: str, delete_files: bool = False) -> bool:
        """Delete profile registration and optionally remove files from disk."""
        p = self.registry.get_profile(profile_id)
        if p and self.lock_manager.is_profile_locked(Path(p.user_data_dir)):
            raise BrowserProfileLockedError(
                code="ERR_BROWSER_PROFILE_LOCKED",
                message=f"Cannot delete profile '{profile_id}' while it is locked or in use.",
                profile_id=profile_id,
            )
        return self.registry.delete_profile(profile_id, delete_files=delete_files)

    def resolve_account(
        self,
        query: Optional[str] = None,
        account_type: Optional[str] = None,
        require_exact: bool = False,
    ) -> BrowserAccountSelection:
        """Resolve account from natural language / voice input (Tamil / English / Tanglish)."""
        return self.selector.resolve(query=query, account_type=account_type, require_exact=require_exact)

    def prepare_profile_for_launch(self, profile_id: str) -> BrowserProfileMetadata:
        """
        Validate path, clear stale locks if needed, acquire lock, and touch last_used_at.
        Raises BrowserProfileLockedError if already locked by another process.
        """
        profile = self.get_profile(profile_id)
        if not profile:
            raise BrowserProfileNotFoundError(
                code="ERR_BROWSER_PROFILE_NOT_FOUND",
                message=f"Profile '{profile_id}' not found in registry.",
                profile_id=profile_id,
            )

        p_dir = Path(profile.user_data_dir)
        # Attempt to clear stale lock if any
        self.lock_manager.clean_stale_locks(p_dir)

        # Acquire lock
        self.lock_manager.acquire_lock(profile_id, p_dir)

        # Update last_used_at timestamp and mark active in registry
        updated = self.registry.update_profile(
            profile_id,
            last_used_at=datetime.datetime.now().isoformat(),
            is_active=True,
        )
        self.registry.set_active_profile(profile_id)
        return updated

    def release_profile(self, profile_id: str) -> None:
        """Release lock and mark profile inactive."""
        profile = self.registry.get_profile(profile_id)
        if profile:
            p_dir = Path(profile.user_data_dir)
            self.lock_manager.release_lock(profile_id, p_dir)
            self.registry.update_profile(profile_id, is_active=False)
            if self.registry.get_active_profile() and self.registry.get_active_profile().profile_id == profile_id:
                self.registry.set_active_profile(None)
