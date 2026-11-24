"""
Browser Tab Management Controller — Day 24.
Handles tab enumeration, tab switching, opening new tabs, and closing tabs safely.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from playwright.async_api import Page

from zye_browser.browser_errors import BrowserAutomationError, BrowserSessionError
from zye_browser.browser_session_manager import BrowserSessionManager
from zye_browser.browser_url_validator import BrowserURLValidator
from zye_browser.models import BrowserTabMetadata

logger = logging.getLogger("ZyeBrowserTabs")


class BrowserTabManager:
    """Manages browser tabs inside the active persistent context."""

    def __init__(self, session_manager: Optional[BrowserSessionManager] = None) -> None:
        self.session_manager = session_manager or BrowserSessionManager.get_instance()

    async def list_tabs(self) -> List[BrowserTabMetadata]:
        """List all open browser tabs with URL, title, and active state."""
        pages = await self.session_manager.get_pages()
        if not pages:
            return []

        tabs: List[BrowserTabMetadata] = []
        for idx, page in enumerate(pages):
            try:
                title = await page.title()
                url = page.url
                is_active = (idx == self.session_manager._active_tab_index)
                tabs.append(
                    BrowserTabMetadata(
                        tab_id=idx,
                        url=url,
                        title=title,
                        is_active=is_active,
                    )
                )
            except Exception as exc:
                logger.debug("Error reading tab %d metadata: %s", idx, exc)
                tabs.append(
                    BrowserTabMetadata(
                        tab_id=idx,
                        url="about:blank",
                        title="[Unknown/Closed]",
                        is_active=False,
                    )
                )

        return tabs

    async def new_tab(self, url: Optional[str] = None) -> BrowserTabMetadata:
        """Open a new browser tab, optionally navigating to a URL."""
        if not self.session_manager._context:
            raise BrowserSessionError(
                code="ERR_BROWSER_NOT_RUNNING",
                message="Cannot open new tab: No active browser session.",
            )

        page = await self.session_manager._context.new_page()
        pages = await self.session_manager.get_pages()
        new_tab_id = len(pages) - 1
        self.session_manager.set_active_tab_index(new_tab_id)

        target_url = "about:blank"
        title = "New Tab"
        if url and url.strip():
            safe_url = BrowserURLValidator.sanitize_and_validate(url)
            await page.goto(safe_url, wait_until="domcontentloaded", timeout=30000)
            target_url = page.url
            title = await page.title()

        return BrowserTabMetadata(
            tab_id=new_tab_id,
            url=target_url,
            title=title,
            is_active=True,
        )

    async def switch_tab(self, tab_id: int) -> BrowserTabMetadata:
        """Switch active focus to the specified tab index."""
        pages = await self.session_manager.get_pages()
        if not (0 <= tab_id < len(pages)):
            raise BrowserAutomationError(
                code="ERR_BROWSER_TAB_INDEX_OUT_OF_RANGE",
                message=f"Tab index {tab_id} out of range (0 to {len(pages)-1}).",
                operation_id=f"switch_tab_{tab_id}",
            )

        page = pages[tab_id]
        await page.bring_to_front()
        self.session_manager.set_active_tab_index(tab_id)

        return BrowserTabMetadata(
            tab_id=tab_id,
            url=page.url,
            title=await page.title(),
            is_active=True,
        )

    async def close_tab(self, tab_id: Optional[int] = None) -> Dict[str, Any]:
        """Close specified tab or active tab."""
        pages = await self.session_manager.get_pages()
        if not pages:
            return {"status": "NO_TABS", "message": "No tabs to close."}

        target_idx = self.session_manager._active_tab_index if tab_id is None else tab_id
        if not (0 <= target_idx < len(pages)):
            raise BrowserAutomationError(
                code="ERR_BROWSER_TAB_INDEX_OUT_OF_RANGE",
                message=f"Tab index {target_idx} is out of range.",
            )

        page_to_close = pages[target_idx]
        await page_to_close.close()

        # Update remaining active index
        pages = await self.session_manager.get_pages()
        if pages:
            new_idx = min(target_idx, len(pages) - 1)
            self.session_manager.set_active_tab_index(new_idx)
            return {
                "status": "SUCCESS",
                "message": f"Closed tab {target_idx}. Active tab is now {new_idx}.",
                "remaining_tabs": len(pages),
                "active_tab_id": new_idx,
            }
        else:
            return {
                "status": "CLOSED_ALL",
                "message": "All tabs were closed.",
                "remaining_tabs": 0,
            }
