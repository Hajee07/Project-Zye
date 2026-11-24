"""
Search Result Ranking & Relevance Scoring Engine.
Computes multi-factor relevance scores based on keyword frequency, exact phrase matching,
domain authority tiers, and content completeness.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("zye.computer_intelligence.result_ranker")

# Official documentation and primary source domains
OFFICIAL_DOMAINS = {
    "docs.python.org", "python.org", "pypi.org",
    "docs.scipy.org", "scipy.org",
    "docs.sympy.org", "sympy.org",
    "numpy.org", "pandas.pydata.org",
    "duckdb.org", "sqlite.org",
    "learn.microsoft.com", "microsoft.com",
    "cloud.google.com", "ai.google.dev", "github.com",
}

ACADEMIC_TECH_DOMAINS = {
    "arxiv.org", "wikipedia.org", "stackoverflow.com", "stackexchange.com",
    "w3.org", "ietf.org", "mozilla.org", "developer.mozilla.org",
}


class SearchResultRanker:
    """Ranks search results using transparent multi-factor scoring."""

    @classmethod
    def calculate_relevance_score(cls, result: dict[str, Any], query: str) -> float:
        """Calculates a normalized score in [0.0, 1.0] for a search result."""
        score = 0.3  # Base score
        query_lower = query.lower().strip()
        keywords = [w for w in re.findall(r"\w+", query_lower) if len(w) > 2]

        title = str(result.get("title", "")).lower()
        snippet = str(result.get("content_snippet", "")).lower()
        source_type = result.get("source_type", "")

        # 1. Exact phrase match bonus
        if query_lower in title:
            score += 0.30
        elif query_lower in snippet:
            score += 0.20

        # 2. Individual keyword frequency match
        if keywords:
            title_hits = sum(1 for k in keywords if k in title)
            snippet_hits = sum(1 for k in keywords if k in snippet)
            keyword_ratio = (title_hits * 2 + snippet_hits) / (len(keywords) * 3)
            score += min(0.25, keyword_ratio * 0.25)

        # 3. Source authority boost
        if source_type == "web":
            domain = str(result.get("domain", "")).lower()
            if any(dom in domain for dom in OFFICIAL_DOMAINS):
                score += 0.20
                result["authority_tier"] = "OFFICIAL_DOCUMENTATION"
            elif any(dom in domain for dom in ACADEMIC_TECH_DOMAINS):
                score += 0.10
                result["authority_tier"] = "TECHNICAL_AUTHORITY"
            else:
                result["authority_tier"] = "GENERAL_WEB"
        elif source_type == "local":
            # Local project files in workspace have high trustworthiness
            score += 0.15
            result["authority_tier"] = "LOCAL_VERIFIED"

        # 4. Content completeness
        if len(snippet) > 100:
            score += 0.05

        return min(1.0, round(score, 4))

    @classmethod
    def rank_results(cls, results: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
        """Scores and sorts search results in descending order of relevance."""
        for res in results:
            res["relevance_score"] = cls.calculate_relevance_score(res, query)

        ranked = sorted(results, key=lambda x: x.get("relevance_score", 0.0), reverse=True)
        return ranked
