"""
Gemini Result Aggregator — Zye Multi-Project Gemini Intelligence Infrastructure v2.0 (Section 10.3).
Aggregates, cross-checks, and synthesizes outputs from multiple decomposed subtask workers.
Detects contradictions, normalizes confidence, and merges multi-perspective findings into unified reports.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("zye.gemini.aggregator")


@dataclass
class SubtaskResult:
    """Output from an individual logical worker role."""
    worker_role: str
    content: str
    status: str = "SUCCESS"  # SUCCESS, FAILED, TIMED_OUT, SKIPPED
    tokens_used: int = 0
    duration_seconds: float = 0.0
    error: str | None = None


@dataclass
class AggregatedResult:
    """Unified synthesis across all completed subtasks."""
    task_id: str
    summary: str
    worker_results: dict[str, SubtaskResult] = field(default_factory=dict)
    contradictions_detected: list[str] = field(default_factory=list)
    total_tokens_used: int = 0
    total_duration_seconds: float = 0.0
    all_successful: bool = True


class GeminiResultAggregator:
    """
    Synthesizes and validates results produced by parallel or sequential subtask workers.
    """

    def aggregate(
        self,
        task_id: str,
        results: list[SubtaskResult],
    ) -> AggregatedResult:
        """
        Aggregate a list of subtask results into a single synthesized result.
        """
        worker_map: dict[str, SubtaskResult] = {}
        total_tokens = 0
        total_duration = 0.0
        all_ok = True
        contradictions: list[str] = []

        for r in results:
            worker_map[r.worker_role] = r
            total_tokens += r.tokens_used
            total_duration += r.duration_seconds
            if r.status != "SUCCESS":
                all_ok = False

        # Detect high-level contradictions between worker perspectives
        sec_result = worker_map.get("SECURITY")
        tech_result = worker_map.get("TECHNICAL")

        if sec_result and tech_result:
            if "reject" in sec_result.content.lower() and "approved" in tech_result.content.lower():
                contradictions.append(
                    "Security worker flagged rejection while Technical worker reported approval."
                )

        # Build synthesized summary text
        summary_sections = [
            f"# Task Synthesis: {task_id}",
            f"**Status:** {'ALL SUBTASKS PASSED' if all_ok else 'PARTIAL / FAILED SUBTASKS'}",
            f"**Total Tokens:** {total_tokens} | **Cumulative Time:** {total_duration:.2f}s\n",
        ]

        if contradictions:
            summary_sections.append("### Contradictions Detected:")
            for c in contradictions:
                summary_sections.append(f"- [WARNING] {c}")
            summary_sections.append("")

        summary_sections.append("### Findings by Role:")
        for role, res in worker_map.items():
            status_tag = f"[{res.status}]" if res.status != "SUCCESS" else ""
            summary_sections.append(f"#### {role} {status_tag}")
            if res.status == "SUCCESS":
                summary_sections.append(res.content.strip())
            else:
                summary_sections.append(f"*Error/Issue:* {res.error or 'Failed without specific error'}")
            summary_sections.append("")

        synthesis_text = "\n".join(summary_sections)

        return AggregatedResult(
            task_id=task_id,
            summary=synthesis_text,
            worker_results=worker_map,
            contradictions_detected=contradictions,
            total_tokens_used=total_tokens,
            total_duration_seconds=total_duration,
            all_successful=all_ok,
        )
