"""
Web Interaction Engine — Day 24.
Handles text typing, keyboard inputs, hovering, and page scrolling safely.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from playwright.async_api import Page

from zye_browser.browser_errors import BrowserAutomationError
from zye_browser.browser_session_manager import BrowserSessionManager
from zye_browser.models import WebInteractionResult
from zye_browser.web_element_resolver import WebElementResolver

logger = logging.getLogger("ZyeInteractionEngine")


class WebInteractionEngine:
    """Executes safe typing, scrolling, and keyboard actions on browser pages."""

    def __init__(
        self,
        session_manager: Optional[BrowserSessionManager] = None,
        resolver: Optional[WebElementResolver] = None,
    ) -> None:
        self.session_manager = session_manager or BrowserSessionManager.get_instance()
        self.resolver = resolver or WebElementResolver(self.session_manager)

    async def type_text(
        self,
        selector_or_text: str,
        text: str,
        press_enter: bool = False,
        clear_first: bool = True,
    ) -> WebInteractionResult:
        """Type text into an input or contenteditable element."""
        page = await self.session_manager.get_active_page()
        try:
            elem = await self.resolver.resolve_element(selector_or_text, allow_ambiguous=True)
            await elem.click()

            if clear_first:
                await elem.fill("")

            await elem.type(text, delay=20)

            if press_enter:
                await elem.press("Enter")
                await page.wait_for_timeout(1000)

            return WebInteractionResult(
                success=True,
                action="type",
                target_selector_or_text=selector_or_text,
                message=f"Successfully typed into '{selector_or_text}'.",
                url_after_action=page.url,
                title_after_action=await page.title(),
            )
        except Exception as exc:
            raise BrowserAutomationError(
                code="ERR_BROWSER_TYPE_FAILED",
                message=f"Failed to type text into '{selector_or_text}': {exc}",
            ) from exc

    async def scroll(self, direction: str = "down", amount: int = 500) -> WebInteractionResult:
        """Scroll the active window up or down."""
        page = await self.session_manager.get_active_page()
        delta = amount if direction.lower() == "down" else -amount
        try:
            await page.evaluate(f"window.scrollBy({{ top: {delta}, behavior: 'smooth' }});")
            await page.wait_for_timeout(500)
            return WebInteractionResult(
                success=True,
                action="scroll",
                message=f"Scrolled {direction} by {amount}px.",
                url_after_action=page.url,
                title_after_action=await page.title(),
            )
        except Exception as exc:
            raise BrowserAutomationError(
                code="ERR_BROWSER_SCROLL_FAILED",
                message=f"Failed to scroll page: {exc}",
            ) from exc

    async def press_key(self, key: str) -> WebInteractionResult:
        """Send a keyboard key press (e.g. 'Enter', 'Escape', 'Tab', 'ArrowDown')."""
        page = await self.session_manager.get_active_page()
        try:
            await page.keyboard.press(key)
            await page.wait_for_timeout(500)
            return WebInteractionResult(
                success=True,
                action="press_key",
                message=f"Pressed keyboard key '{key}'.",
                url_after_action=page.url,
                title_after_action=await page.title(),
            )
        except Exception as exc:
            raise BrowserAutomationError(
                code="ERR_BROWSER_KEYPRESS_FAILED",
                message=f"Failed to press key '{key}': {exc}",
            ) from exc
