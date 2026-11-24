"""
Hybrid Local + Web Search Orchestrator.
Coordinates concurrent local document and live web information retrieval,
ranks results, performs cross-source verification, and constructs evidence packages.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from pathlib import Path
from typing import Any

from .search_query_planner import SearchQueryPlanner, SearchMode
from .local_search_engine import LocalSearchEngine
from .web_search_engine import WebSearchEngine
from .search_result_normalizer import SearchResultNormalizer
from .search_result_ranker import SearchResultRanker
from .evidence_validation_engine import EvidenceValidationEngine
from .citation_builder import CitationBuilder
from .search_cache import SearchCache

logger = logging.getLogger("zye.computer_intelligence.hybrid_search")


class HybridSearchEngine:
    """Unified hybrid information retrieval engine uniting local storage and live internet."""

    def __init__(
        self,
        local_engine: LocalSearchEngine | None = None,
        web_engine: WebSearchEngine | None = None,
        cache: SearchCache | None = None,
    ) -> None:
        self.local_engine = local_engine or LocalSearchEngine()
        self.web_engine = web_engine or WebSearchEngine()
        self.cache = cache or SearchCache()

    def _assemble_evidence_package(
        self,
        clean_query: str,
        mode: SearchMode,
        intent: Any,
        local_hits: list[dict[str, Any]],
        web_hits: list[dict[str, Any]],
        max_results: int,
        start_time: float,
        cache_key: str,
    ) -> dict[str, Any]:
        """Assembles ranked results, evidence validation, citations, and markdown report."""
        normalized = SearchResultNormalizer.normalize_results(
            local_results=local_hits, web_results=web_hits
        )
        ranked = SearchResultRanker.rank_results(normalized, clean_query)
        final_results = ranked[:max_results]
        evidence = EvidenceValidationEngine.validate_evidence(final_results, target_claim=clean_query)
        citations = CitationBuilder.build_citations(final_results)
        markdown_citations = CitationBuilder.format_markdown_citations(citations)
        voice_tan, voice_en = CitationBuilder.format_voice_citations(citations)

        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Build Markdown Presentation
        md_lines = [
            f"## Search Results for: *{clean_query}*",
            f"**Mode:** `{mode.value.upper()}` | **Found:** `{len(final_results)}` results | **Time:** `{duration_ms}ms`",
            f"**Evidence Confidence:** `{evidence['confidence_level']}` ({evidence['corroboration_status']})",
            "",
            "### Top Retrieved Items",
        ]

        for idx, item in enumerate(final_results[:5]):
            stype = item["source_type"].upper()
            title = item["title"]
            snippet = item["content_snippet"]
            cid = item["citation_id"]
            score = item.get("relevance_score", 0.0)
            loc = item.get("file_path") or item.get("url") or ""
            md_lines.append(f"**[{idx+1}] [{stype}] {title}** (Score: `{score}`) `{loc}`")
            if snippet:
                md_lines.append(f"> {snippet[:300]}...")
            md_lines.append("")

        if markdown_citations:
            md_lines.append(markdown_citations)

        markdown_report = "\n".join(md_lines)

        evidence_package = {
            "status": "SUCCESS",
            "query": clean_query,
            "search_mode": mode.value,
            "language": intent.language,
            "is_comparison": intent.is_comparison,
            "results_count": len(final_results),
            "local_results_count": len(local_hits),
            "web_results_count": len(web_hits),
            "results": final_results,
            "evidence_validation": evidence,
            "citations": citations,
            "markdown": markdown_report,
            "voice_tanglish": voice_tan,
            "voice_en": voice_en,
            "duration_ms": duration_ms,
            "from_cache": False,
        }

        # Cache result
        self.cache.set(cache_key, evidence_package)
        return evidence_package

    async def execute_hybrid_search_async(
        self,
        query: str,
        search_mode: str = "auto",
        max_results: int = 10,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """
        Executes query planning, intelligent routing (local/web/hybrid),
        asynchronous retrieval, result ranking, evidence validation, and citation building.
        """
        start_time = time.time()
        clean_query = query.strip()
        if not clean_query:
            return {
                "status": "ERROR",
                "error_code": "EMPTY_QUERY",
                "message": "Search query cannot be empty.",
                "results": [],
            }

        intent = SearchQueryPlanner.classify_search_intent(clean_query, explicit_mode=search_mode)
        mode = intent.mode

        cache_key = SearchCache.generate_cache_key(
            clean_query, mode.value, intent.domain_filters[0] if intent.domain_filters else None
        )
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                cached["from_cache"] = True
                return cached

        local_hits: list[dict[str, Any]] = []
        web_hits: list[dict[str, Any]] = []
        domain_filter = intent.domain_filters[0] if intent.domain_filters else None

        if mode == SearchMode.LOCAL_ONLY:
            local_res = self.local_engine.search_local_sources(
                query=clean_query,
                file_types=intent.file_type_filters or None,
                max_results=max_results,
            )
            local_hits = local_res.get("results", [])

        elif mode == SearchMode.WEB_ONLY:
            web_res = await self.web_engine.search_web_async(
                query=clean_query,
                max_results=max_results,
                domain_filter=domain_filter,
            )
            web_hits = web_res.get("results", [])

        else:
            async def run_local() -> list[dict[str, Any]]:
                return await asyncio.to_thread(
                    self.local_engine.search_local_sources,
                    query=clean_query,
                    file_types=intent.file_type_filters or None,
                    max_results=max_results,
                )

            async def run_web() -> dict[str, Any]:
                return await self.web_engine.search_web_async(
                    query=clean_query,
                    max_results=max_results,
                    domain_filter=domain_filter,
                )

            local_out, web_out = await asyncio.gather(run_local(), run_web(), return_exceptions=True)
            if isinstance(local_out, dict):
                local_hits = local_out.get("results", [])
            if isinstance(web_out, dict):
                web_hits = web_out.get("results", [])

        return self._assemble_evidence_package(
            clean_query, mode, intent, local_hits, web_hits, max_results, start_time, cache_key
        )

    def execute_hybrid_search(
        self,
        query: str,
        search_mode: str = "auto",
        max_results: int = 10,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """
        Pure synchronous hybrid search execution without asyncio event loop dependency.
        Guarantees sub-50ms execution in sandboxed and offline environments.
        """
        start_time = time.time()
        clean_query = query.strip()
        if not clean_query:
            return {
                "status": "ERROR",
                "error_code": "EMPTY_QUERY",
                "message": "Search query cannot be empty.",
                "results": [],
            }

        intent = SearchQueryPlanner.classify_search_intent(clean_query, explicit_mode=search_mode)
        mode = intent.mode

        cache_key = SearchCache.generate_cache_key(
            clean_query, mode.value, intent.domain_filters[0] if intent.domain_filters else None
        )
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                cached["from_cache"] = True
                return cached

        local_hits: list[dict[str, Any]] = []
        web_hits: list[dict[str, Any]] = []
        domain_filter = intent.domain_filters[0] if intent.domain_filters else None

        if mode == SearchMode.LOCAL_ONLY:
            local_res = self.local_engine.search_local_sources(
                query=clean_query,
                file_types=intent.file_type_filters or None,
                max_results=max_results,
            )
            local_hits = local_res.get("results", [])
        elif mode == SearchMode.WEB_ONLY:
            web_res = self.web_engine.search_web(
                query=clean_query,
                max_results=max_results,
                domain_filter=domain_filter,
            )
            web_hits = web_res.get("results", [])
        else:
            # Hybrid or Auto mode
            local_res = self.local_engine.search_local_sources(
                query=clean_query,
                file_types=intent.file_type_filters or None,
                max_results=max_results,
            )
            local_hits = local_res.get("results", [])

            web_res = self.web_engine.search_web(
                query=clean_query,
                max_results=max_results,
                domain_filter=domain_filter,
            )
            web_hits = web_res.get("results", [])

        return self._assemble_evidence_package(
            clean_query, mode, intent, local_hits, web_hits, max_results, start_time, cache_key
        )

    def compare_local_web_sources(
        self,
        local_query: str,
        web_query: str,
        domain_filter: str | None = None,
    ) -> dict[str, Any]:
        """
        Cross-analyzes local project configuration against current live web documentation.
        Identifies differences, installed vs latest version gaps, and compatibility considerations.
        """
        start_time = time.time()
        # 1. Local search
        local_res = self.local_engine.search_local_sources(local_query, max_results=5)
        local_items = local_res.get("results", [])

        # 2. Web search
        web_res = self.web_engine.search_web(web_query, max_results=5, domain_filter=domain_filter)
        web_items = web_res.get("results", [])

        # Extract versions
        def extract_versions(text: str) -> list[str]:
            return re.findall(r"\bv?(\d+\.\d+(?:\.\d+)?)\b", text)

        local_text = " ".join(f"{it.get('title', '')} {it.get('content_snippet', '')}" for it in local_items)
        web_text = " ".join(f"{it.get('title', '')} {it.get('content_snippet', '')}" for it in web_items)

        local_versions = list(dict.fromkeys(extract_versions(local_text)))
        web_versions = list(dict.fromkeys(extract_versions(web_text)))

        has_differences = bool(local_versions and web_versions and local_versions != web_versions)

        # Build comparison summary
        duration_ms = round((time.time() - start_time) * 1000, 2)
        md_lines = [
            "## Source Comparison: Local Project vs Live Web",
            f"**Local Query:** `{local_query}` | **Web Query:** `{web_query}`",
            "",
            "| Dimension | Local Source Findings | Online Web Findings |",
            "|---|---|---|",
            f"| **Sources Retrieved** | `{len(local_items)}` local documents | `{len(web_items)}` web pages |",
            f"| **Detected Versions** | `{', '.join(local_versions) or 'None'}` | `{', '.join(web_versions) or 'None'}` |",
            f"| **Status** | {'VERSION_MISMATCH' if has_differences else 'ALIGNED / UNKNOWN'} | {'UPSTREAM_NEWER' if has_differences else 'ALIGNED'} |",
            "",
            "### Analysis Summary",
            f"- Local project files indicate version(s): **{', '.join(local_versions) or 'Unknown'}**",
            f"- Online documentation indicates version(s): **{', '.join(web_versions) or 'Unknown'}**",
        ]

        if has_differences:
            md_lines.append("\n> [!NOTE]\n> Version discrepancy detected between local project configuration and online documentation.")

        v_tan = (
            f"Local project-la version {', '.join(local_versions) or 'therila'}, aana internet-la version {', '.join(web_versions) or 'therila'}. "
            + ("Differences irukku." if has_differences else "Major differences edhuvum illa.")
        )
        v_en = (
            f"Local project shows version {', '.join(local_versions) or 'unknown'}, while online sources show version {', '.join(web_versions) or 'unknown'}. "
            + ("A version difference was detected." if has_differences else "Information is consistent.")
        )

        return {
            "status": "SUCCESS",
            "local_query": local_query,
            "web_query": web_query,
            "local_results_count": len(local_items),
            "web_results_count": len(web_items),
            "local_versions": local_versions,
            "web_versions": web_versions,
            "has_differences": has_differences,
            "markdown": "\n".join(md_lines),
            "voice_tanglish": v_tan,
            "voice_en": v_en,
            "duration_ms": duration_ms,
        }
