"""
Safe Article Content Retrieval & SSRF Defense Gate (Day 38 / Phase 3).
Executes bounded HTTP fetches with strict network boundary guards, payload size limits,
content sanitization, and prompt injection neutralization.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional, Tuple
import httpx
import lxml.html

from zye_realtime_tactical.news.url_normalizer import UrlNormalizer

logger = logging.getLogger("zye.realtime_tactical.news.content_validator")

# Default limits
DEFAULT_TIMEOUT_SECONDS = 5.0
MAX_CONTENT_BYTES = 512 * 1024  # 500 KB response limit
MAX_REDIRECTS = 3
USER_AGENT = "ZyeVerifiedNewsBot/1.0 (+https://github.com/zye-ai/assistant)"

# Prompt injection markers to neutralize in external web copy
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"reveal\s+(?:your\s+)?api\s+key", re.IGNORECASE),
    re.compile(r"print\s+credentials", re.IGNORECASE),
    re.compile(r"execute\s+command", re.IGNORECASE),
]


class ContentValidator:
    """Safely retrieves and parses article text under strict SSRF protections."""

    @classmethod
    def clean_html_text(cls, raw_html: str) -> str:
        """Parses HTML and extracts clean text without scripts, styles, or tags."""
        try:
            tree = lxml.html.fromstring(raw_html)
            for bad in tree.xpath("//script | //style | //nav | //footer"):
                bad.drop_tree()
            text = tree.text_content()
            return " ".join(text.split())
        except Exception:
            return re.sub(r"<[^>]+>", " ", raw_html).strip()

    @classmethod
    def sanitize_for_prompt_injection(cls, text: str) -> str:
        """Neutralizes adversarial prompt injection patterns found in external news text."""
        sanitized = text
        for pat in PROMPT_INJECTION_PATTERNS:
            sanitized = pat.sub("[POTENTIAL_INJECTION_REDACTED]", sanitized)
        return sanitized

    sanitize_untrusted_text = sanitize_for_prompt_injection

    @classmethod
    async def fetch_article_content(
        cls,
        url: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_bytes: int = MAX_CONTENT_BYTES,
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Fetches and extracts clean textual content from an external news article URL.
        Returns:
            (success: bool, metadata_dict: dict, error_message: Optional[str])
        """
        # 1. Enforce SSRF Defense
        is_safe, reason = UrlNormalizer.is_safe_external_url(url)
        if not is_safe:
            return False, {}, f"SSRF Block: {reason}"

        canonical_url = UrlNormalizer.normalize_url(url)

        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
                timeout=timeout_seconds,
                follow_redirects=True,
                max_redirects=MAX_REDIRECTS,
            ) as client:
                resp = await client.get(canonical_url)

                # Re-validate destination URL after any redirects
                final_safe, final_reason = UrlNormalizer.is_safe_external_url(str(resp.url))
                if not final_safe:
                    return False, {}, f"SSRF Redirect Block: {final_reason}"

                if resp.status_code != 200:
                    return False, {}, f"HTTP {resp.status_code} returned by host"

                # Check Content-Type
                ct = resp.headers.get("content-type", "").lower()
                if "text/html" not in ct and "application/xhtml+xml" not in ct:
                    return False, {}, f"Unsupported Content-Type: {ct}"

                # Content length check
                content_bytes = resp.content
                if len(content_bytes) > max_bytes:
                    content_bytes = content_bytes[:max_bytes]

                html_text = content_bytes.decode("utf-8", errors="replace")

        except httpx.TimeoutException:
            return False, {}, f"Request timed out after {timeout_seconds}s"
        except Exception as exc:
            return False, {}, f"HTTP fetch error: {exc}"

        # 2. Parse HTML and extract clean metadata
        try:
            tree = lxml.html.fromstring(html_text)

            # Extract title
            title_node = tree.xpath("//title/text()")
            title = title_node[0].strip() if title_node else ""

            # Extract publication date from meta tags
            pub_date = None
            date_metas = tree.xpath(
                "//meta[@property='article:published_time']/@content | "
                "//meta[@name='pubdate']/@content | "
                "//meta[@name='publish-date']/@content | "
                "//meta[@name='date']/@content"
            )
            if date_metas:
                pub_date = str(date_metas[0]).strip()

            # Remove noise tags
            for bad_tag in tree.xpath("//script | //style | //nav | //footer | //iframe | //form | //aside"):
                bad_tag.drop_tree()

            # Extract article paragraphs
            paragraphs = tree.xpath("//article//p/text() | //main//p/text() | //p/text()")
            clean_paras = [p.strip() for p in paragraphs if len(p.strip()) > 30]
            body_text = " ".join(clean_paras[:10])  # First 10 key paragraphs

            # Sanitize for prompt injection
            safe_title = cls.sanitize_untrusted_text(title)
            safe_body = cls.sanitize_untrusted_text(body_text)

            return True, {
                "title": safe_title,
                "body": safe_body,
                "meta_published_date": pub_date,
                "content_length": len(safe_body),
                "url": canonical_url,
            }, None

        except Exception as exc:
            return False, {}, f"HTML parsing failure: {exc}"
