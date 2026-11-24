"""
Web Application Detection Engine — Day 24.
Detects active application context from URL and document metadata.
"""

from __future__ import annotations

from urllib.parse import urlparse
from typing import Any, Dict, Optional

from zye_browser.web_app_registry import WebAppRegistry


class WebAppDetector:
    """Detects active web application from current page URL or metadata."""

    def __init__(self, registry: Optional[WebAppRegistry] = None) -> None:
        self.registry = registry or WebAppRegistry()

    def detect(self, url: str) -> Dict[str, Any]:
        """Detect application details from URL."""
        if not url:
            return {"app_key": "unknown", "name": "Unknown", "read_only": True}

        domain = (urlparse(url).hostname or "").lower()

        # Check registered apps
        match = self.registry.get_app_for_domain(domain)
        if match:
            return {
                "app_key": match.get("key"),
                "name": match.get("name", match.get("key")),
                "domain": domain,
                "read_only": match.get("read_only", True),
                "is_google_service": "google" in domain,
            }

        # Check common services
        if "mail.google.com" in domain:
            return {"app_key": "gmail", "name": "Gmail", "domain": domain, "read_only": True, "is_google_service": True}
        if "drive.google.com" in domain:
            return {"app_key": "google_drive", "name": "Google Drive", "domain": domain, "read_only": True, "is_google_service": True}
        if "youtube.com" in domain:
            return {"app_key": "youtube", "name": "YouTube", "domain": domain, "read_only": True, "is_google_service": True}
        if "calendar.google.com" in domain:
            return {"app_key": "calendar", "name": "Google Calendar", "domain": domain, "read_only": True, "is_google_service": True}
        if "google.com" in domain:
            return {"app_key": "google_search", "name": "Google Search", "domain": domain, "read_only": True, "is_google_service": True}

        return {
            "app_key": "generic_web",
            "name": domain or "Web Page",
            "domain": domain,
            "read_only": True,
            "is_google_service": False,
        }
