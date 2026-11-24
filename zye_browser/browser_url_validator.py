"""
Browser URL Validation and Security Enforcement — Day 24.
Enforces safe protocols, prevents local SSRF, blocks dangerous schemas (javascript:, file:, data:).
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse
from typing import Optional

from zye_browser.browser_errors import BrowserNavigationSecurityError

# Blocked schemes
DISALLOWED_SCHEMES = {"javascript", "data", "file", "vbscript", "chrome", "edge"}

# Localhost and loopback regex patterns
LOOPBACK_NAMES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


class BrowserURLValidator:
    """Validates and sanitizes URLs before Playwright navigation."""

    @classmethod
    def sanitize_and_validate(cls, url: str, allow_localhost: bool = False) -> str:
        """
        Validate URL, prepend https:// if missing, and verify safety.
        Raises BrowserNavigationSecurityError on violation.
        """
        if not url or not isinstance(url, str):
            raise BrowserNavigationSecurityError(
                code="ERR_BROWSER_URL_EMPTY",
                message="Target URL cannot be empty.",
                blocked_url=str(url),
            )

        clean_url = url.strip()

        # Handle simple domains without scheme like "google.com" or "mail.google.com"
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*:", clean_url):
            clean_url = f"https://{clean_url}"

        parsed = urlparse(clean_url)
        scheme = parsed.scheme.lower()

        if scheme in DISALLOWED_SCHEMES:
            raise BrowserNavigationSecurityError(
                code="ERR_BROWSER_UNSAFE_SCHEME",
                message=f"Navigation to scheme '{scheme}:' is blocked for security.",
                blocked_url=clean_url,
                remediation="Only http:// and https:// URLs are permitted.",
            )

        if scheme not in {"http", "https"}:
            raise BrowserNavigationSecurityError(
                code="ERR_BROWSER_INVALID_SCHEME",
                message=f"Unsupported URL scheme '{scheme}'. Only http:// and https:// allowed.",
                blocked_url=clean_url,
            )

        hostname = parsed.hostname
        if not hostname:
            raise BrowserNavigationSecurityError(
                code="ERR_BROWSER_MISSING_HOST",
                message="URL is missing a valid host name.",
                blocked_url=clean_url,
            )

        # Localhost / Private IP checks
        if not allow_localhost:
            if hostname.lower() in LOOPBACK_NAMES:
                raise BrowserNavigationSecurityError(
                    code="ERR_BROWSER_LOCAL_HOST_BLOCKED",
                    message=f"Navigation to local host '{hostname}' is blocked unless explicitly enabled.",
                    blocked_url=clean_url,
                )

            # Check if IP address is private
            try:
                ip_obj = ipaddress.ip_address(hostname)
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                    raise BrowserNavigationSecurityError(
                        code="ERR_BROWSER_PRIVATE_IP_BLOCKED",
                        message=f"Navigation to private/internal IP address '{hostname}' is blocked.",
                        blocked_url=clean_url,
                    )
            except ValueError:
                # Hostname is a standard domain name, not a raw IP
                pass

        return clean_url
