"""
Web Element Resolver — Day 24.
Resolves accessible DOM locators (roles, text, aria-labels, CSS) and enforces uniqueness guarantees.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from playwright.async_api import Locator, Page

from zye_browser.browser_errors import DOMElementAmbiguousError, DOMElementNotFoundError
from zye_browser.browser_session_manager import BrowserSessionManager

logger = logging.getLogger("ZyeElementResolver")


class WebElementResolver:
    """Resolves elements safely using accessibility roles, labels, and text."""

    def __init__(self, session_manager: Optional[BrowserSessionManager] = None) -> None:
        self.session_manager = session_manager or BrowserSessionManager.get_instance()

    async def resolve_element(
        self,
        selector_or_text: str,
        role: Optional[str] = None,
        allow_ambiguous: bool = False,
    ) -> Locator:
        """
        Locate unique visible element.
        Raises DOMElementNotFoundError if not found.
        Raises DOMElementAmbiguousError if multiple elements match and allow_ambiguous is False.
        """
        page = await self.session_manager.get_active_page()
        query = selector_or_text.strip()

        # 1. If role is provided, use get_by_role
        if role:
            locator = page.get_by_role(role, name=query)
        elif query.startswith(("//", "xpath=")):
            locator = page.locator(query)
        elif any(c in query for c in [".", "#", "[", ">", ":"]):
            # Likely CSS selector
            locator = page.locator(query)
        else:
            # Try text or label
            locator = page.get_by_text(query, exact=False)

        count = await locator.count()
        if count == 0:
            # Fallback to aria-label match
            locator = page.locator(f"[aria-label*='{query}' i]")
            count = await locator.count()

        if count == 0:
            # Fallback to placeholder match
            locator = page.get_by_placeholder(query)
            count = await locator.count()

        if count == 0:
            raise DOMElementNotFoundError(
                code="ERR_BROWSER_ELEMENT_NOT_FOUND",
                message=f"No visible element found matching '{query}'.",
                selector=query,
                remediation="Inspect page interactive elements with browser_inspect_dom to verify selector or label.",
            )

        if count > 1 and not allow_ambiguous:
            # Check how many are actually visible
            visible_count = 0
            for i in range(count):
                if await locator.nth(i).is_visible():
                    visible_count += 1

            if visible_count > 1:
                raise DOMElementAmbiguousError(
                    code="ERR_BROWSER_ELEMENT_AMBIGUOUS",
                    message=f"Ambiguous target: {visible_count} visible elements match '{query}'.",
                    selector=query,
                    matched_count=visible_count,
                    remediation="Provide a more specific selector, aria-label, or role to identify the target element.",
                )

        return locator.first
