"""
Live Web Search Engine & Provider Abstraction.
Performs live internet search, domain-filtered search, technical documentation search,
and result normalization with graceful offline/fallback handling.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from typing import Any
import httpx
import lxml.html

from zye_computer_intelligence.security.web_url_security import (
    SSRFProtectionPolicy,
    WebSecurityError,
    DEFAULT_HTTP_TIMEOUT_SECONDS,
)
from .web_content_extractor import WebContentExtractor, USER_AGENT

logger = logging.getLogger("zye.computer_intelligence.web_search")


class BaseWebSearchProvider:
    """Abstract base class for web search providers."""

    async def search(
        self,
        query: str,
        max_results: int = 10,
        domain_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError


class DuckDuckGoHtmlProvider(BaseWebSearchProvider):
    """Zero-credential live web search provider querying DuckDuckGo HTML endpoint."""

    SEARCH_ENDPOINT = "https://html.duckduckgo.com/html/"

    def build_search_url(self, query: str, site_filter: str | None = None) -> str:
        """Constructs encoded search query string with optional site filter."""
        import urllib.parse
        full_query = f"{query} site:{site_filter}" if site_filter else query
        return f"{self.SEARCH_ENDPOINT}?q={urllib.parse.quote_plus(full_query)}"

    def parse_search_results(self, html_text: str, max_results: int = 10) -> list[Any]:
        """Parses raw HTML search response into structured result objects."""
        tree = lxml.html.fromstring(html_text)
        result_nodes = tree.xpath("//div[contains(@class, 'result__body')]") or tree.xpath("//div[contains(@class, 'result')]")
        parsed_results = []
        class _ParsedItem:
            def __init__(self, title, url, snippet):
                self.title = title
                self.url = url
                self.snippet = snippet

        for idx, node in enumerate(result_nodes[:max_results]):
            title_elem = node.xpath(".//a[contains(@class, 'result__snippet')] | .//h2//a")
            snippet_elem = node.xpath(".//a[contains(@class, 'result__snippet')] | .//div[contains(@class, 'result__snippet')]")
            if not title_elem:
                continue
            title = (title_elem[0].text_content() or "").strip()
            raw_href = title_elem[0].get("href", "")
            actual_url = raw_href
            if "uddg=" in raw_href:
                parsed_query = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                if "uddg" in parsed_query:
                    actual_url = parsed_query["uddg"][0]
            snippet = (snippet_elem[0].text_content() or "").strip() if snippet_elem else ""
            parsed_results.append(_ParsedItem(title, actual_url, snippet))
        return parsed_results

    async def search(
        self,
        query: str,
        max_results: int = 10,
        domain_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        full_query = f"{query} site:{domain_filter}" if domain_filter else query
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"q": full_query, "b": ""}

        results: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_HTTP_TIMEOUT_SECONDS, follow_redirects=True) as client:
                resp = await client.post(self.SEARCH_ENDPOINT, data=data, headers=headers)
                if resp.status_code != 200:
                    logger.warning("DuckDuckGo returned status %d", resp.status_code)
                    return []

                tree = lxml.html.fromstring(resp.text)
                result_nodes = tree.xpath("//div[contains(@class, 'result__body')]") or tree.xpath("//div[contains(@class, 'result')]")

                for idx, node in enumerate(result_nodes[:max_results]):
                    title_elem = node.xpath(".//a[contains(@class, 'result__snippet')] | .//h2//a")
                    snippet_elem = node.xpath(".//a[contains(@class, 'result__snippet')] | .//div[contains(@class, 'result__snippet')]")

                    if not title_elem:
                        continue

                    title = (title_elem[0].text_content() or "").strip()
                    raw_href = title_elem[0].get("href", "")

                    # DuckDuckGo redirect unwrapping: /l/?uddg=https%3A%2F%2F...
                    actual_url = raw_href
                    if "uddg=" in raw_href:
                        parsed_query = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                        if "uddg" in parsed_query:
                            actual_url = parsed_query["uddg"][0]

                    # Validate URL
                    try:
                        SSRFProtectionPolicy.validate_url(actual_url)
                    except WebSecurityError:
                        continue

                    snippet = (snippet_elem[0].text_content() or "").strip() if snippet_elem else ""
                    domain = urllib.parse.urlparse(actual_url).hostname or ""

                    results.append({
                        "result_id": f"web_{idx+1}",
                        "source_type": "web",
                        "title": title or domain,
                        "url": actual_url,
                        "domain": domain,
                        "content_snippet": snippet[:1000],
                        "citation_id": f"web_{idx+1}",
                    })
        except Exception as e:
            logger.info("Live web search connection unavailable (%s); returning empty web set", e)
            return []

        return results


class WebSearchEngine:
    """Orchestrates live web search, provider routing, and domain filtering."""

    def __init__(self, provider: BaseWebSearchProvider | None = None) -> None:
        self.provider = provider or DuckDuckGoHtmlProvider()

    async def search_web_async(
        self,
        query: str,
        max_results: int = 10,
        domain_filter: str | None = None,
    ) -> dict[str, Any]:
        """Asynchronously executes live web search across provider."""
        clean_query = query.strip()
        if not clean_query:
            return {
                "status": "ERROR",
                "error_code": "EMPTY_WEB_QUERY",
                "message": "Web search query cannot be empty.",
                "results": [],
            }

        try:
            hits = await self.provider.search(
                clean_query, max_results=max_results, domain_filter=domain_filter
            )
            return {
                "status": "SUCCESS",
                "query": clean_query,
                "domain_filter": domain_filter,
                "results_count": len(hits),
                "results": hits,
            }
        except Exception as e:
            logger.warning("Web search engine error: %s", e)
            return {
                "status": "ERROR",
                "error_code": "WEB_SEARCH_FAILED",
                "message": str(e),
                "results": [],
            }

    def search_web(
        self,
        query: str,
        max_results: int = 10,
        domain_filter: str | None = None,
    ) -> dict[str, Any]:
        """Synchronous wrapper for web search."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        asyncio.run,
                        self.search_web_async(query, max_results, domain_filter)
                    ).result()
            else:
                return loop.run_until_complete(
                    self.search_web_async(query, max_results, domain_filter)
                )
        except Exception:
            return asyncio.run(self.search_web_async(query, max_results, domain_filter))

    def search_web_by_domain(self, query: str, domain: str, max_results: int = 10) -> dict[str, Any]:
        """Executes domain-restricted web search (e.g. site:docs.python.org)."""
        clean_domain = domain.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
        return self.search_web(query, max_results=max_results, domain_filter=clean_domain)
