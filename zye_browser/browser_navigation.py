"""
Browser Navigation Controller — Day 24.
Handles URL navigation, shortcuts for Google services (Gmail, Drive, YouTube, Calendar), and page history.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from urllib.parse import quote_plus

from zye_browser.browser_errors import BrowserAutomationError, BrowserSessionError
from zye_browser.browser_session_manager import BrowserSessionManager
from zye_browser.browser_url_validator import BrowserURLValidator

logger = logging.getLogger("ZyeBrowserNavigation")


class BrowserNavigationController:
    """Manages page navigation, direct web app URLs, and navigation history."""

    APP_URLS = {
        "gmail": "https://mail.google.com",
        "drive": "https://drive.google.com",
        "youtube": "https://www.youtube.com",
        "calendar": "https://calendar.google.com",
        "search": "https://www.google.com",
        "maps": "https://maps.google.com",
        "news": "https://news.google.com",
    }

    def __init__(self, session_manager: Optional[BrowserSessionManager] = None) -> None:
        self.session_manager = session_manager or BrowserSessionManager.get_instance()

    async def navigate(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout_ms: int = 30000,
        allow_localhost: bool = False,
    ) -> Dict[str, Any]:
        """Navigate active tab to a sanitized, validated target URL."""
        page = await self.session_manager.get_active_page()
        clean_url = BrowserURLValidator.sanitize_and_validate(url, allow_localhost=allow_localhost)

        try:
            response = await page.goto(clean_url, wait_until=wait_until, timeout=timeout_ms)
            status_code = response.status if response else 200
            current_url = page.url
            title = await page.title()

            return {
                "status": "SUCCESS",
                "requested_url": clean_url,
                "current_url": current_url,
                "title": title,
                "http_status": status_code,
            }
        except Exception as exc:
            raise BrowserAutomationError(
                code="ERR_BROWSER_NAVIGATE_FAILED",
                message=f"Failed to navigate to '{clean_url}': {exc}",
                operation_id="navigate",
            ) from exc

    async def open_app(self, app_name: str, query: Optional[str] = None) -> Dict[str, Any]:
        """Navigate to a known Google Web App or shortcut."""
        clean_name = app_name.strip().lower()

        if clean_name == "search" and query:
            target_url = f"https://www.google.com/search?q={quote_plus(query.strip())}"
        elif clean_name == "youtube" and query:
            target_url = f"https://www.youtube.com/results?search_query={quote_plus(query.strip())}"
        elif clean_name == "gmail" and query:
            target_url = f"https://mail.google.com/mail/u/0/#search/{quote_plus(query.strip())}"
        elif clean_name == "drive" and query:
            target_url = f"https://drive.google.com/drive/search?q={quote_plus(query.strip())}"
        elif clean_name in self.APP_URLS:
            target_url = self.APP_URLS[clean_name]
        else:
            target_url = f"https://www.google.com/search?q={quote_plus(app_name)}"

        return await self.navigate(target_url)

    async def go_back(self) -> Dict[str, Any]:
        """Navigate back in history."""
        page = await self.session_manager.get_active_page()
        try:
            await page.go_back(wait_until="domcontentloaded", timeout=15000)
            return {
                "status": "SUCCESS",
                "action": "go_back",
                "current_url": page.url,
                "title": await page.title(),
            }
        except Exception as exc:
            raise BrowserAutomationError(
                code="ERR_BROWSER_HISTORY_BACK_FAILED",
                message=f"Failed to go back: {exc}",
            ) from exc

    async def go_forward(self) -> Dict[str, Any]:
        """Navigate forward in history."""
        page = await self.session_manager.get_active_page()
        try:
            await page.go_forward(wait_until="domcontentloaded", timeout=15000)
            return {
                "status": "SUCCESS",
                "action": "go_forward",
                "current_url": page.url,
                "title": await page.title(),
            }
        except Exception as exc:
            raise BrowserAutomationError(
                code="ERR_BROWSER_HISTORY_FORWARD_FAILED",
                message=f"Failed to go forward: {exc}",
            ) from exc

    async def reload(self) -> Dict[str, Any]:
        """Reload the active page."""
        page = await self.session_manager.get_active_page()
        try:
            await page.reload(wait_until="domcontentloaded", timeout=20000)
            return {
                "status": "SUCCESS",
                "action": "reload",
                "current_url": page.url,
                "title": await page.title(),
            }
        except Exception as exc:
            raise BrowserAutomationError(
                code="ERR_BROWSER_RELOAD_FAILED",
                message=f"Failed to reload page: {exc}",
            ) from exc
