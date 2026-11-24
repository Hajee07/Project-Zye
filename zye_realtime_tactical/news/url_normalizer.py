"""
URL and Domain Normalization Engine (Day 38 / Phase 3).
Normalizes article URLs, strips tracking query parameters, derives canonical domains,
and enforces SSRF security protections.
"""

from __future__ import annotations

import ipaddress
import re
import socket
import urllib.parse
from typing import Optional, Set, Tuple


# Known tracking parameters to strip for canonical URL deduplication
TRACKING_PARAMS: Set[str] = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "fbclid",
    "gclid",
    "dclid",
    "msclkid",
    "mc_cid",
    "mc_eid",
    "ocid",
    "ncid",
    "ref",
    "ref_src",
    "_ga",
    "_gl",
    "sr_share",
}

# Common multi-part TLD suffixes for accurate registrable domain extraction
MULTI_PART_TLDS: Set[str] = {
    "co.uk",
    "org.uk",
    "gov.uk",
    "ac.uk",
    "co.in",
    "org.in",
    "net.in",
    "gov.in",
    "com.au",
    "net.au",
    "org.au",
    "co.jp",
    "ne.jp",
    "co.nz",
    "com.br",
    "com.sg",
}


class UrlNormalizer:
    """Provides deterministic URL canonicalization and domain identity resolution."""

    @classmethod
    def normalize_url(cls, raw_url: str) -> str:
        """
        Produces a canonicalized URL:
        - Ensures http/https scheme.
        - Lowercases hostname.
        - Strips tracking parameters.
        - Removes redundant ports (:80, :443) and trailing slashes.
        """
        if not raw_url or not isinstance(raw_url, str):
            raise ValueError(f"Invalid URL input: {raw_url}")

        url = raw_url.strip()
        parsed = urllib.parse.urlsplit(url)

        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https"):
            raise ValueError(f"Unsupported URL scheme '{scheme}'. Only http and https permitted.")

        netloc = (parsed.hostname or parsed.netloc.split(":")[0]).lower()
        while netloc.startswith("www."):
            netloc = netloc[4:]
        if parsed.port and not ((scheme == "http" and parsed.port == 80) or (scheme == "https" and parsed.port == 443)):
            netloc = f"{netloc}:{parsed.port}"

        # Strip tracking query parameters
        clean_query = ""
        if parsed.query:
            query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
            filtered = [
                (k, v) for k, v in query_pairs if k.lower() not in TRACKING_PARAMS and not k.startswith("utm_")
            ]
            if filtered:
                clean_query = urllib.parse.urlencode(filtered)

        path = parsed.path
        if path.endswith("/") and len(path) > 1:
            path = path.rstrip("/")

        # Reconstruct canonical URL (discard fragments for news articles)
        canonical = urllib.parse.urlunsplit((scheme, netloc, path, clean_query, ""))
        return canonical

    @classmethod
    def extract_canonical_domain(cls, url: str) -> str:
        """
        Extracts the registrable or canonical domain from an article URL:
        e.g., 'https://edition.cnn.com/world/news' -> 'cnn.com'
              'https://news.bbc.co.uk/articles/1' -> 'bbc.co.uk'
              'https://timesofindia.indiatimes.com/tech' -> 'indiatimes.com'
        """
        try:
            parsed = urllib.parse.urlsplit(url)
            host = (parsed.hostname or parsed.netloc.split(":")[0]).lower()
        except Exception:
            host = url.lower()

        # Strip www prefixes
        while host.startswith("www."):
            host = host[4:]

        parts = host.split(".")
        if len(parts) <= 2:
            return host

        # Check multi-part TLDs (e.g. co.uk, co.in)
        last_two = ".".join(parts[-2:])
        if last_two in MULTI_PART_TLDS and len(parts) >= 3:
            return ".".join(parts[-3:])

        # Standard registrable domain (e.g. edition.cnn.com -> cnn.com)
        return ".".join(parts[-2:])

    @classmethod
    def is_safe_external_url(cls, url: str) -> Tuple[bool, Optional[str]]:
        """
        SSRF Defense Gate:
        Rejects localhost, loopback, private RFC-1918, link-local, and cloud metadata (169.254.169.254).
        """
        try:
            parsed = urllib.parse.urlsplit(url)
            if parsed.scheme.lower() not in ("http", "https"):
                return False, f"Prohibited scheme: {parsed.scheme}"

            host = (parsed.hostname or parsed.netloc.split(":")[0]).strip("[] \t").lower()
            if not host:
                return False, "Missing hostname"

            # Check localhost aliases
            if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
                return False, "Localhost destination prohibited"

            # Cloud metadata address check
            if host == "169.254.169.254":
                return False, "Cloud metadata service address prohibited"

            # If host is an IP address, verify it is not private/loopback/reserved
            try:
                ip = ipaddress.ip_address(host)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
                    return False, f"Private or reserved IP address blocked: {ip}"
            except ValueError:
                # Host is a domain name, check for suspicious internal domain suffixes
                lower_host = host.lower()
                if (
                    lower_host.endswith(".local")
                    or lower_host.endswith(".internal")
                    or lower_host.endswith(".lan")
                    or lower_host.endswith(".corp")
                ):
                    return False, f"Internal domain blocked: {host}"

            return True, None
        except Exception as exc:
            return False, f"URL security parsing failure: {exc}"

    # Backward-compatible alias
    validate_url_ssrf_safe = is_safe_external_url
