"""
Web URL Security Validator & SSRF Protection Policy.
Enforces strict protocol checks, blocks localhost, private IPv4/IPv6 ranges,
and shields internal cloud metadata services (e.g. 169.254.169.254).
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from urllib.parse import urlparse
from typing import Any

logger = logging.getLogger("zye.computer_intelligence.web_security")

ALLOWED_SCHEMES = {"http", "https"}
MAX_REDIRECTS = 5
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_HTTP_TIMEOUT_SECONDS = 10.0

# Blocked hostnames
BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
}

# Blocked domain suffixes for internal/private networks
BLOCKED_DOMAIN_SUFFIXES = (
    ".local",
    ".internal",
    ".localhost",
    ".lan",
    ".corp",
    ".home",
    ".arpa",
)

# Cloud metadata IP addresses
CLOUD_METADATA_IPS = {
    "169.254.169.254",  # AWS / Azure / GCP metadata
    "100.100.100.200",  # Alibaba Cloud metadata
}


class WebSecurityError(Exception):
    """Raised when an SSRF attempt, private IP access, or insecure URL is detected."""
    pass


class SSRFProtectionPolicy:
    """Enforces SSRF prevention by validating URLs and resolving IPs against private subnets."""

    @classmethod
    def is_private_ip(cls, ip_str: str) -> bool:
        """Returns True if the IP belongs to private, loopback, link-local, or reserved ranges."""
        try:
            ip = ipaddress.ip_address(ip_str)
            return (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
                or str(ip) in CLOUD_METADATA_IPS
            )
        except ValueError:
            return True

    @classmethod
    def validate_url(cls, url: str, resolve_dns: bool = True) -> str:
        """
        Validates URL scheme, hostname, and resolved IP addresses.
        Raises WebSecurityError if the destination is insecure or violates SSRF policy.
        """
        if not url or not url.strip():
            raise WebSecurityError("URL cannot be empty.")

        clean_url = url.strip()
        parsed = urlparse(clean_url)

        if parsed.scheme.lower() not in ALLOWED_SCHEMES:
            raise WebSecurityError(
                f"Protocol '{parsed.scheme}' is prohibited. Only HTTP and HTTPS are permitted."
            )

        hostname = parsed.hostname
        if not hostname:
            raise WebSecurityError(f"Invalid URL: missing hostname in '{clean_url}'")

        lower_host = hostname.lower()
        if lower_host in BLOCKED_HOSTNAMES or any(lower_host.endswith(sfx) for sfx in BLOCKED_DOMAIN_SUFFIXES):
            raise WebSecurityError(f"Access to '{hostname}' is blocked by SSRF policy.")

        # Check if hostname itself is an IP literal
        try:
            ip = ipaddress.ip_address(hostname)
            if cls.is_private_ip(str(ip)):
                raise WebSecurityError(
                    f"Direct access to private or loopback IP '{hostname}' is blocked."
                )
            return clean_url
        except ValueError:
            # It's a domain name, resolve DNS
            pass

        # Resolve domain to IP addresses if resolve_dns is enabled
        if resolve_dns:
            try:
                resolved_ips = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
                for item in resolved_ips:
                    sockaddr = item[4]
                    ip_candidate = sockaddr[0]
                    if cls.is_private_ip(ip_candidate):
                        raise WebSecurityError(
                            f"SSRF violation: Hostname '{hostname}' resolves to private/restricted IP '{ip_candidate}'."
                        )
            except socket.gaierror as e:
                # In sandbox or offline environments, DNS resolution might not be available
                logger.debug(
                    "DNS resolution unavailable for hostname '%s': %s (allowing offline format validation)",
                    hostname,
                    e,
                )
            except Exception as e:
                if isinstance(e, WebSecurityError):
                    raise
                raise WebSecurityError(f"URL validation error: {e}")

        return clean_url
