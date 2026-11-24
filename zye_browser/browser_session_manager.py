"""
Async Browser Session Manager — Day 24.
Manages persistent Playwright context, active pages, window lifecycle, and session status.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from zye_browser.browser_errors import BrowserAutomationError, BrowserSessionError
from zye_browser.models import BrowserSessionStatus, BrowserTabMetadata
from zye_browser.profile_manager import ProfileManager

logger = logging.getLogger("ZyeBrowserSession")


class BrowserSessionManager:
    """Singleton manager for active Playwright persistent browser context and pages."""

    _instance: Optional["BrowserSessionManager"] = None

    def __init__(self, profile_manager: Optional[ProfileManager] = None) -> None:
        self.profile_manager = profile_manager or ProfileManager()
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._active_profile_id: Optional[str] = None
        self._start_time: Optional[datetime.datetime] = None
        self._last_activity_time: Optional[datetime.datetime] = None
        self._headless: bool = False
        self._chrome_version: Optional[str] = None
        self._active_tab_index: int = 0
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        """Lazily initialize asyncio.Lock in the active event loop."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    @classmethod
    def get_instance(cls, profile_manager: Optional[ProfileManager] = None) -> "BrowserSessionManager":
        """Get or initialize singleton instance."""
        if cls._instance is None:
            cls._instance = BrowserSessionManager(profile_manager)
        return cls._instance

    @property
    def is_running(self) -> bool:
        """Check if browser context is active and not closed."""
        return self._context is not None and len(self._context.pages) > 0

    async def launch_session(
        self,
        profile_id: str,
        headless: bool = False,
        channel: str = "chrome",
        viewport: Optional[Dict[str, int]] = None,
    ) -> BrowserSessionStatus:
        """
        Launch a persistent browser session for the specified profile.
        If another session is active, closes it cleanly first.
        """
        async with self._get_lock():
            if self.is_running:
                if self._active_profile_id == profile_id:
                    logger.info("Session for profile '%s' is already running.", profile_id)
                    return await self.get_status_async()
                else:
                    logger.info("Closing previous session '%s' to switch to '%s'.", self._active_profile_id, profile_id)
                    await self._close_internal()

            # 1. Prepare profile & acquire lock
            profile = self.profile_manager.prepare_profile_for_launch(profile_id)
            user_data_path = Path(profile.user_data_dir)

            # 2. Launch Playwright
            try:
                if self._playwright is None:
                    self._playwright = await async_playwright().start()

                # Launch persistent context
                args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-default-browser-check",
                    "--disable-features=IsolateOrigins,site-per-process",
                ]

                # Default viewport or natural window
                vp = viewport if viewport else {"width": 1280, "height": 850}

                try:
                    self._context = await self._playwright.chromium.launch_persistent_context(
                        user_data_dir=str(user_data_path),
                        headless=headless,
                        channel=channel,
                        args=args,
                        viewport=vp,
                        accept_downloads=True,
                    )
                except Exception as chrome_err:
                    logger.warning("Could not launch with channel='%s': %s. Retrying with default chromium.", channel, chrome_err)
                    self._context = await self._playwright.chromium.launch_persistent_context(
                        user_data_dir=str(user_data_path),
                        headless=headless,
                        args=args,
                        viewport=vp,
                        accept_downloads=True,
                    )

                self._active_profile_id = profile_id
                self._headless = headless
                self._start_time = datetime.datetime.now()
                self._last_activity_time = datetime.datetime.now()

                # Ensure at least one tab is open
                if not self._context.pages:
                    await self._context.new_page()

                # Try fetching browser version
                try:
                    p = self._context.pages[0]
                    self._chrome_version = await p.evaluate("() => navigator.userAgent")
                except Exception:
                    self._chrome_version = "Chrome/Chromium"

                logger.info("Launched persistent browser session for profile '%s' (headless=%s).", profile_id, headless)
                return await self.get_status_async()

            except Exception as exc:
                # Clean up lock on failure
                self.profile_manager.release_profile(profile_id)
                self._active_profile_id = None
                raise BrowserSessionError(
                    code="ERR_BROWSER_LAUNCH_FAILED",
                    message=f"Failed to launch browser session for profile '{profile_id}': {exc}",
                    profile_id=profile_id,
                ) from exc

    async def get_active_page(self) -> Page:
        """Retrieve the currently focused or active page."""
        if not self._context or not self._context.pages:
            raise BrowserSessionError(
                code="ERR_BROWSER_NOT_RUNNING",
                message="No active browser session is currently running.",
                profile_id=self._active_profile_id,
                remediation="Launch a browser session first using browser_launch_session.",
            )

        pages = self._context.pages
        if 0 <= self._active_tab_index < len(pages):
            page = pages[self._active_tab_index]
        else:
            page = pages[0]
            self._active_tab_index = 0

        self._last_activity_time = datetime.datetime.now()
        return page

    async def get_pages(self) -> List[Page]:
        """Return all open pages in active context."""
        if not self._context:
            return []
        return self._context.pages

    def set_active_tab_index(self, index: int) -> None:
        """Set the active tab index."""
        if self._context and 0 <= index < len(self._context.pages):
            self._active_tab_index = index
            self._last_activity_time = datetime.datetime.now()

    async def close_session(self) -> None:
        """Cleanly close active context and release profile lock."""
        async with self._get_lock():
            await self._close_internal()

    async def _close_internal(self) -> None:
        """Internal close procedure without acquiring lock again."""
        if self._context:
            try:
                await self._context.close()
            except Exception as exc:
                logger.warning("Error closing browser context: %s", exc)
            self._context = None

        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as exc:
                logger.warning("Error stopping Playwright: %s", exc)
            self._playwright = None

        if self._active_profile_id:
            try:
                self.profile_manager.release_profile(self._active_profile_id)
            except Exception as exc:
                logger.warning("Error releasing profile lock: %s", exc)

        self._active_profile_id = None
        self._start_time = None
        self._active_tab_index = 0
        logger.info("Browser session closed cleanly.")

    def get_status(self) -> BrowserSessionStatus:
        """Build status snapshot of active browser session synchronously."""
        if not self._context or not self._context.pages:
            return BrowserSessionStatus(is_running=False)

        pages = self._context.pages
        profile = self.profile_manager.get_profile(self._active_profile_id) if self._active_profile_id else None
        uptime = (datetime.datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0

        return BrowserSessionStatus(
            is_running=True,
            active_profile_id=self._active_profile_id,
            active_profile_name=profile.display_name if profile else None,
            chrome_version=self._chrome_version,
            headless=self._headless,
            tabs_count=len(pages),
            user_data_dir=profile.user_data_dir if profile else None,
            uptime_seconds=uptime,
            last_activity_at=self._last_activity_time.isoformat() if self._last_activity_time else None,
        )

    async def get_status_async(self) -> BrowserSessionStatus:
        """Build status snapshot of active browser session."""
        if not self._context or not self._context.pages:
            return BrowserSessionStatus(is_running=False)

        pages = self._context.pages
        profile = self.profile_manager.get_profile(self._active_profile_id) if self._active_profile_id else None

        active_tab_meta: Optional[BrowserTabMetadata] = None
        try:
            active_page = await self.get_active_page()
            url = active_page.url
            title = await active_page.title()
            active_tab_meta = BrowserTabMetadata(
                tab_id=self._active_tab_index,
                url=url,
                title=title,
                is_active=True,
            )
        except Exception:
            pass

        uptime = (datetime.datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0

        return BrowserSessionStatus(
            is_running=True,
            active_profile_id=self._active_profile_id,
            active_profile_name=profile.display_name if profile else None,
            chrome_version=self._chrome_version,
            headless=self._headless,
            tabs_count=len(pages),
            active_tab=active_tab_meta,
            user_data_dir=profile.user_data_dir if profile else None,
            uptime_seconds=uptime,
            last_activity_at=self._last_activity_time.isoformat() if self._last_activity_time else None,
        )
