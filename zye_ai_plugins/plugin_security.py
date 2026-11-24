"""
ZYE AI — Plugin Security & SSRF Protection (Day 25)
Enforces API key isolation, secret masking, URL scheme validation,
and SSRF protection for all external and local AI providers.
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

# Blocked private networks for external provider endpoints
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

# Common API key and credential detection patterns
_SECRET_PATTERNS = [
    re.compile(r"(sk-[a-zA-Z0-9_-]{20,})"),
    re.compile(r"(AIzaSy[a-zA-Z0-9_-]{33})"),
    re.compile(r"([a-zA-Z0-9_-]{32,64}\b)"),
]


def mask_secret(secret: str | None) -> str:
    """Mask an API key or token, exposing only the prefix and suffix."""
    if not secret:
        return "[NOT_CONFIGURED]"
    clean = str(secret).strip()
    if len(clean) <= 8:
        return "****"
    if clean.startswith("sk-"):
        return f"sk-...{clean[-4:]}"
    return f"{clean[:3]}...{clean[-4:]}"


def validate_endpoint_url(url: str, allow_localhost: bool = False, allow_loopback: bool = False) -> tuple[bool, str]:
    """
    Validate that an endpoint URL is safe from SSRF and meets security standards.
    Returns (is_valid, error_message).
    """
    effective_allow_local = allow_localhost or allow_loopback
    if not url or not isinstance(url, str):
        return False, "URL is empty or invalid"

    try:
        parsed = urlparse(url.strip())
    except Exception as exc:
        return False, f"Malformed URL: {exc}"

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return False, f"Unsupported URL scheme '{scheme}'. Only http and https are allowed."

    host = parsed.hostname
    if not host:
        return False, "Missing hostname in URL."

    host_lower = host.lower()

    # Localhost handling
    if host_lower in ("localhost", "127.0.0.1", "::1"):
        if effective_allow_local:
            return True, ""
        return False, "Localhost access is not permitted for external AI providers."

    # External providers MUST use HTTPS
    if not effective_allow_local and scheme != "https":
        return False, "External AI provider endpoints must strictly use HTTPS."

    # IP address inspection for private subnets
    try:
        ip = ipaddress.ip_address(host)
        for net in _BLOCKED_NETWORKS:
            if ip in net:
                if effective_allow_local and ip.is_loopback:
                    return True, ""
                return False, f"Access to private IP space '{ip}' is blocked for security."
    except ValueError:
        # Host is a domain name, check for forbidden patterns
        if host_lower.endswith(".internal") or host_lower.endswith(".local") or host_lower == "metadata.google.internal":
            return False, f"Access to internal domain '{host}' is prohibited."

    return True, ""


def sanitize_prompt(prompt: str) -> str:
    """
    Redact obvious secrets from prompts before sending to external AI providers.
    """
    if not prompt:
        return ""
    sanitized = prompt
    # Redact Google Gemini / OpenAI keys
    sanitized = re.sub(r"AIzaSy[a-zA-Z0-9_-]{30,}", "[REDACTED_API_KEY]", sanitized)
    sanitized = re.sub(r"sk-[a-zA-Z0-9_-]{20,}", "[REDACTED_API_KEY]", sanitized)
    return sanitized
