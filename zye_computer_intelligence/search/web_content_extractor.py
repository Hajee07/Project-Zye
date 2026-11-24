"""
Web Content Extractor & HTML Sanitization Engine.
Safely fetches web pages via HTTPX, validates against SSRF, strips scripts/ads/cookie banners,
and extracts clean structured content, headings, and tables.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse
from typing import Any
import httpx
import lxml.html

from zye_computer_intelligence.security.web_url_security import (
    SSRFProtectionPolicy,
    WebSecurityError,
    MAX_DOWNLOAD_BYTES,
    DEFAULT_HTTP_TIMEOUT_SECONDS,
)
from zye_computer_intelligence.security.untrusted_content_guard import UntrustedContentGuard

logger = logging.getLogger("zye.computer_intelligence.web_extractor")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 ZyeAI/3.0"


class WebContentExtractor:
    """Safely retrieves external web pages, strips noise, and extracts core content."""

    @classmethod
    async def fetch_and_extract_async(
        cls,
        url: str,
        timeout: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
        max_bytes: int = MAX_DOWNLOAD_BYTES,
    ) -> dict[str, Any]:
        """Asynchronously fetches web page, verifies SSRF safety, and extracts clean text."""
        try:
            validated_url = SSRFProtectionPolicy.validate_url(url)
        except WebSecurityError as e:
            return {
                "status": "ERROR",
                "error_code": "WEB_URL_BLOCKED",
                "message": str(e),
                "url": url,
            }

        headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, max_redirects=5) as client:
                resp = await client.get(validated_url, headers=headers)
                if resp.status_code != 200:
                    return {
                        "status": "ERROR",
                        "error_code": "WEB_FETCH_FAILED",
                        "http_status": resp.status_code,
                        "message": f"Server responded with HTTP status {resp.status_code}",
                        "url": validated_url,
                    }

                # Verify response size
                content_bytes = resp.content
                if len(content_bytes) > max_bytes:
                    return {
                        "status": "ERROR",
                        "error_code": "WEB_CONTENT_OVERSIZED",
                        "message": f"Web content size {len(content_bytes)} bytes exceeds limit {max_bytes} bytes.",
                        "url": validated_url,
                    }

                html_text = resp.text
                return cls.extract_from_html(html_text, source_url=str(resp.url))
        except httpx.TimeoutException:
            return {
                "status": "ERROR",
                "error_code": "WEB_FETCH_TIMEOUT",
                "message": f"Connection timed out after {timeout} seconds.",
                "url": validated_url,
            }
        except Exception as e:
            logger.warning("Web page fetch failed for '%s': %s", validated_url, e)
            return {
                "status": "ERROR",
                "error_code": "WEB_EXTRACTION_FAILED",
                "message": str(e),
                "url": validated_url,
            }

    @classmethod
    def fetch_and_extract(
        cls,
        url: str,
        timeout: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
        max_bytes: int = MAX_DOWNLOAD_BYTES,
    ) -> dict[str, Any]:
        """Synchronous wrapper for web page fetching and content extraction."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In running event loop, create task or run in executor
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, cls.fetch_and_extract_async(url, timeout, max_bytes)).result()
            else:
                return loop.run_until_complete(cls.fetch_and_extract_async(url, timeout, max_bytes))
        except Exception:
            # Fallback to direct sync httpx call
            return cls._fetch_sync(url, timeout, max_bytes)

    @classmethod
    def _fetch_sync(cls, url: str, timeout: float, max_bytes: int) -> dict[str, Any]:
        try:
            validated_url = SSRFProtectionPolicy.validate_url(url)
            headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
            with httpx.Client(timeout=timeout, follow_redirects=True, max_redirects=5) as client:
                resp = client.get(validated_url, headers=headers)
                if resp.status_code != 200:
                    return {
                        "status": "ERROR",
                        "error_code": "WEB_FETCH_FAILED",
                        "http_status": resp.status_code,
                        "message": f"Server responded with HTTP status {resp.status_code}",
                        "url": validated_url,
                    }
                if len(resp.content) > max_bytes:
                    return {"status": "ERROR", "error_code": "WEB_CONTENT_OVERSIZED", "url": validated_url}
                return cls.extract_from_html(resp.text, source_url=str(resp.url))
        except Exception as e:
            return {"status": "ERROR", "error_code": "WEB_FETCH_ERROR", "message": str(e), "url": url}

    @classmethod
    def parse_html(cls, html_content: str, source_url: str = "") -> Any:
        """Helper for unit tests returning attributes like title, text_content, paragraphs."""
        extracted = cls.extract_from_html(html_content, source_url=source_url)
        tree = lxml.html.fromstring(html_content) if html_content.strip() else None
        meta_desc = ""
        paragraphs = []
        if tree is not None:
            desc_elem = tree.xpath("//meta[@name='description']/@content")
            if desc_elem:
                meta_desc = str(desc_elem[0])
            for p in tree.xpath("//p"):
                txt = (p.text_content() or "").strip()
                if txt:
                    paragraphs.append(txt)

        class _HtmlResult:
            def __init__(self, data: dict[str, Any], meta: str, paras: list[str]):
                self.title = data.get("title", "")
                self.text_content = data.get("content", "")
                self.meta_description = meta
                self.paragraphs = paras
                self.url = data.get("url", "")
                self.headings = data.get("headings", [])
        return _HtmlResult(extracted, meta_desc, paragraphs)

    @classmethod
    def extract_from_html(cls, html_content: str, source_url: str = "") -> dict[str, Any]:
        """Parses HTML DOM with lxml.html, removes noise, and extracts clean article text."""
        try:
            tree = lxml.html.fromstring(html_content)

            # Strip scripts, styles, forms, navigation, footers, and cookie banners
            for el in tree.xpath("//script | //style | //nav | //footer | //header | //aside | //form | //noscript"):
                el.drop_tree()

            title = (tree.findtext(".//title") or "").strip()
            domain = urlparse(source_url).hostname if source_url else ""

            # Extract headings
            headings = []
            for h in tree.xpath("//h1 | //h2 | //h3"):
                htxt = (h.text_content() or "").strip()
                if htxt:
                    headings.append(htxt)

            # Extract paragraphs
            paragraphs = []
            for p in tree.xpath("//p | //article | //main"):
                ptxt = (p.text_content() or "").strip()
                if len(ptxt) > 30:
                    paragraphs.append(ptxt)

            # Join main text
            full_text = "\n\n".join(paragraphs) if paragraphs else tree.text_content()
            clean_text = " ".join(full_text.split())

            # Guard against prompt injection inside web page
            guarded = UntrustedContentGuard.sanitize_untrusted_text(clean_text, source_label=source_url or title)

            snippet = guarded["sanitized_text"][:1000]

            return {
                "status": "SUCCESS",
                "title": title or domain or "Web Document",
                "domain": domain,
                "url": source_url,
                "headings": headings[:15],
                "content": guarded["sanitized_text"][:50000],
                "snippet": snippet,
                "word_count": len(clean_text.split()),
                "injection_detected": guarded["injection_detected"],
            }
        except Exception as e:
            logger.warning("HTML DOM parsing error: %s", e)
            return {
                "status": "ERROR",
                "error_code": "HTML_PARSING_ERROR",
                "message": str(e),
                "url": source_url,
                "content": "",
                "snippet": "",
            }
