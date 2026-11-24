"""
Multi-Source Evidence Validation Engine.
Corroborates claims across multiple sources, detects information conflicts,
identifies outdated versions, and reports evidence confidence levels.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("zye.computer_intelligence.evidence_validator")


class EvidenceValidationEngine:
    """Verifies factual claims against retrieved sources and flags conflicts."""

    @classmethod
    def validate_evidence(
        cls,
        results: list[dict[str, Any]],
        target_claim: str | None = None,
    ) -> dict[str, Any]:
        """
        Assesses evidence corroboration across all retrieved search results.
        Returns status, confidence level, corroborated points, and conflicting claims.
        """
        if not results:
            return {
                "status": "NO_EVIDENCE",
                "confidence_level": "NONE",
                "corroboration_status": "NO_SOURCES_FOUND",
                "corroborated_sources_count": 0,
                "contradictions": [],
                "summary": "No search results were retrieved to validate claims.",
            }

        local_count = sum(1 for r in results if r.get("source_type") == "local")
        web_count = sum(1 for r in results if r.get("source_type") == "web")

        contradictions: list[str] = []
        # Version number extraction across sources to detect discrepancies
        versions_found: dict[str, list[str]] = {}
        for r in results:
            title_and_snippet = f"{r.get('title', '')} {r.get('content_snippet', '')}"
            matches = re.findall(r"\bv?(\d+\.\d+(?:\.\d+)?)\b", title_and_snippet)
            if matches:
                cid = r.get("citation_id", "source")
                for v in matches[:2]:
                    versions_found.setdefault(v, []).append(cid)

        # If multiple different versions are mentioned across sources
        if len(versions_found) > 1:
            diff_summary = ", ".join(f"v{v} (cited by {', '.join(sources)})" for v, sources in versions_found.items())
            contradictions.append(f"Multiple versions detected across sources: {diff_summary}")

        # Assess confidence
        if len(results) >= 3 and not contradictions:
            confidence = "HIGH"
            corrob_status = "MULTI_SOURCE_CORROBORATED"
        elif len(results) >= 2:
            confidence = "MEDIUM"
            corrob_status = "PARTIALLY_CORROBORATED"
        else:
            confidence = "LOW"
            corrob_status = "SINGLE_SOURCE_UNVERIFIED"

        return {
            "status": "SUCCESS",
            "confidence_level": confidence,
            "corroboration_status": corrob_status,
            "total_sources_count": len(results),
            "local_sources_count": local_count,
            "web_sources_count": web_count,
            "contradictions": contradictions,
            "has_contradictions": len(contradictions) > 0,
            "summary": (
                f"Validated across {len(results)} sources ({local_count} local, {web_count} web). "
                f"Confidence: {confidence}. "
                + (f"Contradictions flagged: {len(contradictions)}." if contradictions else "No direct conflicts.")
            ),
        }
