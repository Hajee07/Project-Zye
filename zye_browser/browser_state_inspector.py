"""
Browser State and Readiness Inspector — Day 24.
Inspects active page state, DOM readyState, detects login/auth gates, and active application domain.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from zye_browser.browser_session_manager import BrowserSessionManager

logger = logging.getLogger("ZyeBrowserInspector")


class BrowserStateInspector:
    """Inspects page readiness, URL domains, and login challenge screens."""

    LOGIN_PATTERNS = [
        "accounts.google.com/signin",
        "accounts.google.com/v3/signin",
        "accounts.google.com/ServiceLogin",
        "login.microsoftonline.com",
        "github.com/login",
        "auth.services.mozilla.com",
    ]

    def __init__(self, session_manager: Optional[BrowserSessionManager] = None) -> None:
        self.session_manager = session_manager or BrowserSessionManager.get_instance()

    async def inspect_state(self) -> Dict[str, Any]:
        """Inspect current state of active page and browser."""
        if not self.session_manager.is_running:
            return {
                "is_running": False,
                "message": "Browser session is not running.",
            }

        page = await self.session_manager.get_active_page()
        url = page.url
        title = await page.title()

        # Evaluate DOM readyState and basic metrics
        try:
            metrics = await page.evaluate(
                """() => ({
                    readyState: document.readyState,
                    viewportWidth: window.innerWidth,
                    viewportHeight: window.innerHeight,
                    domain: window.location.hostname,
                    linksCount: document.querySelectorAll('a').length,
                    inputsCount: document.querySelectorAll('input, textarea, select').length,
                    buttonsCount: document.querySelectorAll('button').length,
                })"""
            )
        except Exception as exc:
            metrics = {
                "readyState": "unknown",
                "error": str(exc),
            }

        is_login = any(pat in url for pat in self.LOGIN_PATTERNS)
        app_type = self._detect_app_type(url)

        return {
            "is_running": True,
            "profile_id": self.session_manager._active_profile_id,
            "url": url,
            "title": title,
            "app_type": app_type,
            "is_login_page": is_login,
            "metrics": metrics,
        }

    def _detect_app_type(self, url: str) -> str:
        """Categorize URL into known service types."""
        domain = urlparse(url).hostname or ""
        domain = domain.lower()

        if "mail.google.com" in domain:
            return "gmail"
        if "drive.google.com" in domain or "docs.google.com" in domain:
            return "drive"
        if "youtube.com" in domain:
            return "youtube"
        if "calendar.google.com" in domain:
            return "calendar"
        if "google.com" in domain:
            return "google_search"
        return "web_generic"
