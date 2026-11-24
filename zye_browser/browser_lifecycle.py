"""
Browser Lifecycle Controller — Day 24.
Orchestrates profile-aware browser start, stop, restart, profile switching, and responsiveness checks.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from zye_browser.browser_errors import (
    BrowserAccountSelectionRequiredError,
    BrowserSessionError,
)
from zye_browser.browser_session_manager import BrowserSessionManager
from zye_browser.models import BrowserSessionStatus
from zye_browser.profile_manager import ProfileManager

logger = logging.getLogger("ZyeBrowserLifecycle")


class BrowserLifecycleController:
    """High-level lifecycle controller for browser automation."""

    def __init__(
        self,
        session_manager: Optional[BrowserSessionManager] = None,
        profile_manager: Optional[ProfileManager] = None,
    ) -> None:
        self.profile_manager = profile_manager or ProfileManager()
        self.session_manager = session_manager or BrowserSessionManager.get_instance(self.profile_manager)

    async def start(
        self,
        account_query: Optional[str] = None,
        headless: bool = False,
    ) -> BrowserSessionStatus:
        """
        Start browser session, resolving profile if query provided.
        If disambiguation is required, raises BrowserAccountSelectionRequiredError.
        """
        # Resolve profile
        selection = self.profile_manager.resolve_account(account_query)
        if not selection.matched or not selection.profile:
            raise BrowserAccountSelectionRequiredError(
                code="ERR_BROWSER_ACCOUNT_SELECTION_REQUIRED",
                message=selection.selection_prompt or "Please specify which account to launch.",
                candidates=[p.model_dump() for p in selection.candidates],
                selection_prompt=selection.selection_prompt,
            )

        target_profile_id = selection.profile.profile_id
        return await self.session_manager.launch_session(
            profile_id=target_profile_id,
            headless=headless,
        )

    async def stop(self) -> Dict[str, Any]:
        """Stop running browser session."""
        active_id = self.session_manager._active_profile_id
        await self.session_manager.close_session()
        return {
            "status": "STOPPED",
            "message": f"Browser session for profile '{active_id}' closed successfully.",
            "closed_profile_id": active_id,
        }

    async def restart(self, headless: Optional[bool] = None) -> BrowserSessionStatus:
        """Restart currently running browser session."""
        active_id = self.session_manager._active_profile_id
        if not active_id:
            raise BrowserSessionError(
                code="ERR_BROWSER_NOT_RUNNING",
                message="Cannot restart: No browser session is currently running.",
            )

        current_headless = self.session_manager._headless if headless is None else headless
        await self.session_manager.close_session()
        return await self.session_manager.launch_session(
            profile_id=active_id,
            headless=current_headless,
        )

    async def switch_profile(self, new_account_query: str, headless: bool = False) -> BrowserSessionStatus:
        """Switch active session to another profile."""
        selection = self.profile_manager.resolve_account(new_account_query)
        if not selection.matched or not selection.profile:
            raise BrowserAccountSelectionRequiredError(
                code="ERR_BROWSER_ACCOUNT_SELECTION_REQUIRED",
                message=selection.selection_prompt or f"Cannot switch to '{new_account_query}'.",
                candidates=[p.model_dump() for p in selection.candidates],
                selection_prompt=selection.selection_prompt,
            )

        new_profile_id = selection.profile.profile_id
        return await self.session_manager.launch_session(
            profile_id=new_profile_id,
            headless=headless,
        )

    async def is_responsive(self) -> bool:
        """Probe browser page responsiveness via light DOM evaluation."""
        if not self.session_manager.is_running:
            return False
        try:
            page = await self.session_manager.get_active_page()
            res = await page.evaluate("() => 1 + 1")
            return res == 2
        except Exception:
            return False
