"""
Analysis Report Builder.
Constructs Section 38/46 JSON responses incorporating dataset profiling, statistics, and execution metrics.
"""

from __future__ import annotations

import time
from typing import Any
import uuid


class AnalysisReportBuilder:
    """Builds comprehensive structured reports."""

    @staticmethod
    def build_report(
        dataset_meta: dict[str, Any],
        backend: str,
        profile: dict[str, Any] | None = None,
        statistics: dict[str, Any] | None = None,
        correlations: dict[str, Any] | None = None,
        trends: dict[str, Any] | None = None,
        outliers: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
        duration_ms: float = 0.0,
        peak_memory_mb: float | None = None,
        rows_scanned: int | None = None,
    ) -> dict[str, Any]:
        """Assembles a verified Section 38 compliant analytical report."""
        analysis_id = f"ana_{uuid.uuid4().hex[:12]}"

        report_warnings = list(warnings or [])
        if correlations and correlations.get("noncausality_statement"):
            if correlations["noncausality_statement"] not in report_warnings:
                report_warnings.append(correlations["noncausality_statement"])

        return {
            "analysis_id": analysis_id,
            "status": "SUCCESS",
            "dataset": {
                "name": dataset_meta.get("file_name", "dataset"),
                "file_path": dataset_meta.get("file_path", ""),
                "format": dataset_meta.get("format", "CSV"),
                "size_mb": dataset_meta.get("size_mb", 0.0),
                "rows": rows_scanned or dataset_meta.get("schema", {}).get("row_count", 0),
                "columns": dataset_meta.get("schema", {}).get("column_names", []),
            },
            "backend": backend,
            "profile": profile or {},
            "statistics": statistics or {},
            "correlations": correlations or {},
            "trends": trends or {},
            "outliers": outliers or {},
            "warnings": report_warnings,
            "limitations": [
                "Analysis performed on current file snapshot.",
                "Statistical correlations do not imply causal relationships.",
                "Outliers reflect statistical distance from distribution center and require domain review.",
            ],
            "execution": {
                "duration_ms": round(duration_ms, 2),
                "peak_memory_mb": peak_memory_mb,
                "rows_scanned": rows_scanned,
            },
        }
