"""
Unified Web Application Search Engine — Day 24.
Executes targeted in-app searches across Gmail, Drive, YouTube, and generic web search bars.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
from playwright.async_api import Page

from zye_browser.browser_errors import BrowserAutomationError
from zye_browser.browser_session_manager import BrowserSessionManager
from zye_browser.models import WebSearchResult
from zye_browser.web_app_detector import WebAppDetector

logger = logging.getLogger("ZyeWebAppSearch")


class WebAppSearchEngine:
    """Executes searches within web applications or search engines."""

    SEARCH_SELECTORS = {
        "gmail": [
            "input[aria-label='Search mail']",
            "input[aria-label*='Search']",
            "input[name='q']",
        ],
        "google_drive": [
            "input[aria-label='Search in Drive']",
            "input[aria-label*='Search']",
            "input[name='q']",
        ],
        "youtube": [
            "input[name='search_query']",
            "input#search",
            "input[placeholder*='Search']",
        ],
        "google_search": [
            "textarea[name='q']",
            "input[name='q']",
            "input[title='Search']",
        ],
        "generic": [
            "input[type='search']",
            "input[name*='search' i]",
            "input[aria-label*='search' i]",
            "input[placeholder*='search' i]",
            "input[role='searchbox']",
        ],
    }

    def __init__(
        self,
        session_manager: Optional[BrowserSessionManager] = None,
        detector: Optional[WebAppDetector] = None,
    ) -> None:
        self.session_manager = session_manager or BrowserSessionManager.get_instance()
        self.detector = detector or WebAppDetector()

    async def search(self, query: str, app_override: Optional[str] = None) -> WebSearchResult:
        """
        Execute in-app search for the current active page or specified app.
        Waits for results and returns structured WebSearchResult.
        """
        page = await self.session_manager.get_active_page()
        clean_query = query.strip()
        if not clean_query:
            raise BrowserAutomationError(
                code="ERR_BROWSER_EMPTY_SEARCH_QUERY",
                message="Search query cannot be empty.",
            )

        detected = self.detector.detect(page.url)
        target_app = (app_override or detected["app_key"]).lower()

        # Handle specific URL-based search shortcuts when appropriate
        if target_app == "gmail":
            return await self._search_gmail(page, clean_query)
        elif target_app == "google_drive" or target_app == "drive":
            return await self._search_drive(page, clean_query)
        elif target_app == "youtube":
            return await self._search_youtube(page, clean_query)
        elif target_app == "google_search":
            return await self._search_google(page, clean_query)
        else:
            return await self._search_generic(page, clean_query)

    async def _search_gmail(self, page: Page, query: str) -> WebSearchResult:
        """Search in Gmail via search box or direct URL hash."""
        try:
            # Try filling search input if present
            found_input = False
            for sel in self.SEARCH_SELECTORS["gmail"]:
                locator = page.locator(sel).first
                if await locator.count() > 0 and await locator.is_visible():
                    await locator.click()
                    await locator.fill(query)
                    await locator.press("Enter")
                    found_input = True
                    break

            if not found_input:
                # Direct hash navigation
                await page.goto(f"https://mail.google.com/mail/u/0/#search/{quote_plus(query)}", wait_until="domcontentloaded")

            # Wait briefly for results to populate
            await page.wait_for_timeout(2000)

            return WebSearchResult(
                query=query,
                target_app="gmail",
                total_results_found=1,  # Evaluated by gmail adapter
                snapshot_preview=f"Searched Gmail for: {query}",
            )
        except Exception as exc:
            raise BrowserAutomationError(
                code="ERR_BROWSER_GMAIL_SEARCH_FAILED",
                message=f"Failed to search Gmail: {exc}",
            ) from exc

    async def _search_drive(self, page: Page, query: str) -> WebSearchResult:
        """Search in Google Drive."""
        try:
            found_input = False
            for sel in self.SEARCH_SELECTORS["google_drive"]:
                locator = page.locator(sel).first
                if await locator.count() > 0 and await locator.is_visible():
                    await locator.click()
                    await locator.fill(query)
                    await locator.press("Enter")
                    found_input = True
                    break

            if not found_input:
                await page.goto(f"https://drive.google.com/drive/search?q={quote_plus(query)}", wait_until="domcontentloaded")

            await page.wait_for_timeout(2000)

            return WebSearchResult(
                query=query,
                target_app="google_drive",
                total_results_found=1,
                snapshot_preview=f"Searched Google Drive for: {query}",
            )
        except Exception as exc:
            raise BrowserAutomationError(
                code="ERR_BROWSER_DRIVE_SEARCH_FAILED",
                message=f"Failed to search Google Drive: {exc}",
            ) from exc

    async def _search_youtube(self, page: Page, query: str) -> WebSearchResult:
        """Search on YouTube."""
        target_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        await page.goto(target_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        return WebSearchResult(
            query=query,
            target_app="youtube",
            total_results_found=1,
            snapshot_preview=f"Searched YouTube for: {query}",
        )

    async def _search_google(self, page: Page, query: str) -> WebSearchResult:
        """Search on Google."""
        target_url = f"https://www.google.com/search?q={quote_plus(query)}"
        await page.goto(target_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        return WebSearchResult(
            query=query,
            target_app="google_search",
            total_results_found=1,
            snapshot_preview=f"Searched Google for: {query}",
        )

    async def _search_generic(self, page: Page, query: str) -> WebSearchResult:
        """Search on generic webpage using available search inputs."""
        for sel in self.SEARCH_SELECTORS["generic"]:
            locator = page.locator(sel).first
            if await locator.count() > 0 and await locator.is_visible():
                await locator.click()
                await locator.fill(query)
                await locator.press("Enter")
                await page.wait_for_timeout(1500)
                return WebSearchResult(
                    query=query,
                    target_app="generic_web",
                    total_results_found=1,
                    snapshot_preview=f"Submitted search on page with selector '{sel}'",
                )

        raise BrowserAutomationError(
            code="ERR_BROWSER_SEARCH_INPUT_NOT_FOUND",
            message="No visible search input found on current page.",
            remediation="Ensure page contains a visible search field or navigate directly with search URL.",
        )
