"""
Safe Web Click Engine — Day 24.
Executes mouse clicks with element ambiguity checks and high-stakes financial/deletion safeguards.
"""

from __future__ import annotations

import logging
from typing import Optional
from playwright.async_api import Page

from zye_browser.browser_errors import BrowserAutomationError
from zye_browser.browser_session_manager import BrowserSessionManager
from zye_browser.models import WebInteractionResult
from zye_browser.web_element_resolver import WebElementResolver

logger = logging.getLogger("ZyeClickEngine")


class WebClickEngine:
    """Safe click execution engine enforcing uniqueness and safety barriers."""

    # Keywords for destructive or irreversible actions requiring explicit confirmation
    DANGEROUS_ACTIONS = [
        "delete account", "confirm purchase", "pay now", "buy now",
        "place order", "send money", "transfer funds", "permanently delete",
        "wipe data", "empty trash"
    ]

    def __init__(
        self,
        session_manager: Optional[BrowserSessionManager] = None,
        resolver: Optional[WebElementResolver] = None,
    ) -> None:
        self.session_manager = session_manager or BrowserSessionManager.get_instance()
        self.resolver = resolver or WebElementResolver(self.session_manager)

    async def click(
        self,
        selector_or_text: str,
        role: Optional[str] = None,
        allow_ambiguous: bool = False,
        confirmed: bool = False,
    ) -> WebInteractionResult:
        """
        Safely click an element.
        Enforces uniqueness check and blocks critical financial/destructive actions without confirmation.
        """
        page = await self.session_manager.get_active_page()
        clean_target = selector_or_text.strip()
        lower_target = clean_target.lower()

        # 1. Safety check for high-stakes actions
        if any(act in lower_target for act in self.DANGEROUS_ACTIONS) and not confirmed:
            return WebInteractionResult(
                success=False,
                action="click",
                target_selector_or_text=clean_target,
                message=f"High-stakes action '{clean_target}' blocked. User explicit confirmation is required before proceeding.",
                requires_confirmation=True,
                url_after_action=page.url,
                title_after_action=await page.title(),
            )

        # 2. Resolve element safely
        elem = await self.resolver.resolve_element(
            selector_or_text=clean_target,
            role=role,
            allow_ambiguous=allow_ambiguous,
        )

        # 3. Perform click
        try:
            await elem.click(timeout=10000)
            # Wait briefly for potential DOM updates or navigation
            await page.wait_for_timeout(1000)

            return WebInteractionResult(
                success=True,
                action="click",
                target_selector_or_text=clean_target,
                message=f"Successfully clicked element '{clean_target}'.",
                url_after_action=page.url,
                title_after_action=await page.title(),
            )
        except Exception as exc:
            raise BrowserAutomationError(
                code="ERR_BROWSER_CLICK_FAILED",
                message=f"Failed to click element '{clean_target}': {exc}",
                remediation="Ensure element is visible and not covered by modals or overlays.",
            ) from exc
