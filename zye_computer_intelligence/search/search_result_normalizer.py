"""
Search Result Normalization Engine.
Normalizes heterogeneous local document and live web results into a unified schema,
suppresses duplicate URLs and paths, and assigns persistent citation identifiers.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse
from typing import Any

logger = logging.getLogger("zye.computer_intelligence.result_normalizer")


class SearchResultNormalizer:
    """Normalizes heterogeneous search results into standard schema with citation IDs."""

    @classmethod
    def normalize_results(
        cls,
        local_results: list[dict[str, Any]] | None = None,
        web_results: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Combines and normalizes local and web search hits with unique citation IDs."""
        normalized: list[dict[str, Any]] = []
        seen_identifiers: set[str] = set()

        # 1. Process local results
        if local_results:
            for item in local_results:
                fpath = item.get("file_path", "")
                if fpath and fpath in seen_identifiers:
                    continue
                if fpath:
                    seen_identifiers.add(fpath)

                cid = f"local_{len(normalized)+1}"
                normalized.append({
                    "result_id": item.get("result_id", cid),
                    "source_type": "local",
                    "title": item.get("title", item.get("file_name", "Local File")),
                    "file_path": fpath,
                    "file_name": item.get("file_name", ""),
                    "file_type": item.get("file_type", "unknown"),
                    "file_size": item.get("file_size", 0),
                    "url": None,
                    "domain": None,
                    "content_snippet": item.get("content_snippet", "").strip(),
                    "match_type": item.get("match_type", "LOCAL_SEARCH"),
                    "citation_id": cid,
                })

        # 2. Process web results
        if web_results:
            for item in web_results:
                raw_url = item.get("url", "")
                if raw_url:
                    # Canonical URL deduplication
                    parsed = urlparse(raw_url)
                    canonical = f"{parsed.netloc}{parsed.path}".rstrip("/")
                    if canonical in seen_identifiers:
                        continue
                    seen_identifiers.add(canonical)

                cid = f"web_{len(normalized)+1}"
                normalized.append({
                    "result_id": item.get("result_id", cid),
                    "source_type": "web",
                    "title": item.get("title", item.get("domain", "Web Page")),
                    "file_path": None,
                    "file_name": None,
                    "file_type": "web_page",
                    "file_size": None,
                    "url": raw_url,
                    "domain": item.get("domain", urlparse(raw_url).hostname or ""),
                    "content_snippet": item.get("content_snippet", "").strip(),
                    "match_type": item.get("match_type", "WEB_SEARCH"),
                    "citation_id": cid,
                })

        return normalized
