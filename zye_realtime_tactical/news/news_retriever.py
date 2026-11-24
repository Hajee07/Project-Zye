"""
News Search Provider & Retrieval Adapter (Day 38 / Phase 3).
Executes live news searches via DuckDuckGo News Search (DDGS) in asyncio background threads,
with timeout handling, mock test provider injection, and robust offline fallback capabilities.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("zye.realtime_tactical.news.retriever")


class NewsRetriever:
    """Retrieves live news articles with non-blocking async execution and provider abstraction."""

    _mock_provider: Optional[Callable[[str, int], List[Dict[str, Any]]]] = None

    @classmethod
    def set_mock_provider(
        cls, provider_fn: Optional[Callable[[str, int], List[Dict[str, Any]]]]
    ) -> None:
        """Injects a mock search function for deterministic offline testing and CI/CD suites."""
        cls._mock_provider = provider_fn

    @classmethod
    def reset_mock_provider(cls) -> None:
        """Clears the mock search provider."""
        cls._mock_provider = None

    @classmethod
    def _execute_ddgs_sync(
        cls,
        topic: str,
        max_results: int = 8,
        region: str = "us-en",
    ) -> List[Dict[str, Any]]:
        """Synchronous DDGS news search executed within a worker thread."""
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            try:
                from ddgs import DDGS
            except ImportError:
                raise RuntimeError("Neither 'duckduckgo_search' nor 'ddgs' library is installed.")

        with DDGS() as ddgs:
            raw_results = list(
                ddgs.news(
                    keywords=topic,
                    region=region,
                    safesearch="moderate",
                    max_results=max_results,
                )
            )
        return raw_results

    @classmethod
    def fetch_news_results_sync(
        cls,
        topic: str,
        max_results: int = 8,
    ) -> Tuple[str, List[Dict[str, Any]], Optional[str]]:
        """Synchronously retrieves news items (e.g. for offline mock tests or sync scripts)."""
        clean_topic = topic.strip()
        if not clean_topic:
            return "NO_RESULTS", [], "Topic query is empty."

        if cls._mock_provider is not None:
            try:
                mock_items = cls._mock_provider(clean_topic, max_results)
                if not mock_items:
                    return "NO_RESULTS", [], "Mock provider returned 0 articles."
                return "SUCCESS", mock_items, None
            except Exception as exc:
                return "NEWS_PROVIDER_UNAVAILABLE", [], f"Mock provider error: {exc}"

        try:
            raw_items = cls._execute_ddgs_sync(clean_topic, max_results)
            if not raw_items:
                return "NO_RESULTS", [], f"Zero news results discovered for topic: '{clean_topic}'"
            return "SUCCESS", raw_items, None
        except Exception as exc:
            return "NEWS_PROVIDER_UNAVAILABLE", [], f"Search provider failure: {exc}"

    @classmethod
    async def fetch_news_results(
        cls,
        topic: str,
        max_results: int = 8,
        timeout_seconds: float = 10.0,
    ) -> Tuple[str, List[Dict[str, Any]], Optional[str]]:
        """
        Asynchronously retrieves news items for the given topic.
        Returns:
            (status: str, raw_items: list, error_message: Optional[str])
        Status values:
            - SUCCESS: Search completed and returned results
            - NO_RESULTS: Search executed successfully but found 0 articles
            - NEWS_PROVIDER_UNAVAILABLE: Library missing, network offline, or rate limited
            - NEWS_SEARCH_TIMEOUT: Search did not complete within timeout
        """
        clean_topic = topic.strip()
        if not clean_topic:
            return "NO_RESULTS", [], "Topic query is empty."

        # Check if mock provider is active (for offline unit tests)
        if cls._mock_provider is not None:
            try:
                mock_items = cls._mock_provider(clean_topic, max_results)
                if not mock_items:
                    return "NO_RESULTS", [], "Mock provider returned 0 articles."
                return "SUCCESS", mock_items, None
            except Exception as exc:
                return "NEWS_PROVIDER_UNAVAILABLE", [], f"Mock provider error: {exc}"

        try:
            raw_items = await asyncio.wait_for(
                asyncio.to_thread(cls._execute_ddgs_sync, clean_topic, max_results),
                timeout=timeout_seconds,
            )

            if not raw_items:
                return "NO_RESULTS", [], f"Zero news results discovered for topic: '{clean_topic}'"

            return "SUCCESS", raw_items, None

        except asyncio.TimeoutError:
            logger.warning("DDGS news search timed out after %s seconds for '%s'", timeout_seconds, clean_topic)
            return "NEWS_SEARCH_TIMEOUT", [], f"News search exceeded timeout limit ({timeout_seconds}s)"
        except Exception as exc:
            logger.error("DDGS news retrieval failure for '%s': %s", clean_topic, exc, exc_info=True)
            return "NEWS_PROVIDER_UNAVAILABLE", [], f"Search provider failure: {exc}"
