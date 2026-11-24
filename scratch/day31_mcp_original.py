"""
ZYE AI — Computer Intelligence MCP Server (Day 31 / Phase 3)
Big Data Intelligence, Columnar Analytics, DuckDB Engine & Statistical Computing.

Exposes 11 FastMCP tools for schema inspection, dataset profiling, correlation analysis,
group aggregation, time-series trends, and statistical anomaly detection.
"""

from __future__ import annotations

import logging
from pathlib import Path
import time
from typing import Any
from mcp.server.fastmcp import FastMCP

from zye_computer_intelligence.data_engine.dataset_loader import DatasetLoader
from zye_computer_intelligence.data_engine.duckdb_engine import ManagedDuckDB
from zye_computer_intelligence.statistics.correlation_engine import CorrelationEngine
from zye_computer_intelligence.statistics.summary_statistics import SummaryStatistics
from zye_computer_intelligence.statistics.segment_analytics import SegmentAnalytics
from zye_computer_intelligence.statistics.trend_engine import TrendEngine
from zye_computer_intelligence.statistics.anomaly_engine import AnomalyEngine
from zye_computer_intelligence.reporting.analysis_report import AnalysisReportBuilder
from zye_computer_intelligence.reporting.result_formatter import ResultFormatter
from zye_computer_intelligence.security.resource_policy import JobManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("zye.computer_intelligence.mcp")

mcp = FastMCP("computer_intelligence")
job_manager = JobManager()


# ---------------------------------------------------------------------------
# Tool 1: Schema Inspection
# ---------------------------------------------------------------------------
@mcp.tool()
def inspect_dataset_schema(file_path: str, sheet_name: str | None = None) -> dict[str, Any]:
    """Inspects dataset source metadata, row counts, columns, and data types without full loading."""
    loaded = DatasetLoader.load_and_inspect(file_path, sheet_name=sheet_name)
    if loaded["status"] != "SUCCESS":
        return loaded

    schema = loaded["schema"]
    return {
        "status": "SUCCESS",
        "file_name": loaded["file_name"],
        "format": loaded["format"],
        "backend": loaded["backend"],
        "size_mb": loaded["size_mb"],
        "row_count": schema.get("row_count", 0),
        "column_count": schema.get("column_count", 0),
        "columns": schema.get("columns", []),
        "numeric_columns": schema.get("numeric_columns", []),
        "categorical_columns": schema.get("categorical_columns", []),
        "date_columns": schema.get("date_columns", []),
        "identifier_columns": schema.get("identifier_columns", []),
    }


# ---------------------------------------------------------------------------
# Tool 2: Dataset Profiling
# ---------------------------------------------------------------------------
@mcp.tool()
def profile_large_dataset(file_path: str, sheet_name: str | None = None) -> dict[str, Any]:
    """Generates complete statistical and data-quality profile including nulls, distincts, and distributions."""
    t0 = time.perf_counter()
    loaded = DatasetLoader.load_and_inspect(file_path, sheet_name=sheet_name)
    if loaded["status"] != "SUCCESS":
        return loaded

    schema = loaded["schema"]
    num_cols = schema.get("numeric_columns", [])
    cat_cols = schema.get("categorical_columns", [])
    all_cols = schema.get("column_names", [])

    with ManagedDuckDB() as engine:
        source_sql = schema.get("read_sql") or engine.get_csv_read_sql(file_path)

        num_profiles = SummaryStatistics.profile_numeric_columns(engine, source_sql, num_cols)
        cat_profiles = SummaryStatistics.profile_categorical_columns(engine, source_sql, cat_cols)
        missing_info = SummaryStatistics.analyze_missing_values(engine, source_sql, all_cols)
        dup_info = SummaryStatistics.analyze_duplicate_rows(engine, source_sql)

    duration_ms = (time.perf_counter() - t0) * 1000

    report = AnalysisReportBuilder.build_report(
        dataset_meta=loaded,
        backend=loaded["backend"],
        profile={
            "missing_values": missing_info,
            "duplicate_records": dup_info,
            "categorical_profiles": cat_profiles,
        },
        statistics={"numeric_distributions": num_profiles},
        duration_ms=duration_ms,
        rows_scanned=schema.get("row_count", 0),
    )
    voice_tan, voice_en = ResultFormatter.format_voice_summaries(report)
    markdown = ResultFormatter.format_markdown_report(report)

    report["markdown"] = markdown
    report["voice_tanglish"] = voice_tan
    report["voice_en"] = voice_en
    return report


# ---------------------------------------------------------------------------
# Tool 3: General Large Dataset Analysis
# ---------------------------------------------------------------------------
@mcp.tool()
def analyze_large_dataset(
    file_path: str,
    operation: str = "DATASET_PROFILE",
    group_by: list[str] | None = None,
    metric: str | None = None,
    aggregation: str = "SUM",
    date_column: str | None = None,
    time_interval: str = "MONTH",
    sort_desc: bool = True,
    limit: int = 50,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Executes validated large dataset analysis according to specified operation."""
    op_upper = operation.strip().upper()
    if op_upper == "DATASET_PROFILE":
        return profile_large_dataset(file_path, sheet_name=sheet_name)
    elif op_upper in ("GROUP_AGGREGATE", "SEGMENT_COMPARISON") and group_by and metric:
        return aggregate_dataset_by_group(
            file_path=file_path,
            group_by=group_by,
            metric=metric,
            aggregation=aggregation,
            sort_desc=sort_desc,
            limit=limit,
            sheet_name=sheet_name,
        )
    elif op_upper == "TIME_TREND" and date_column and metric:
        return analyze_dataset_trends(
            file_path=file_path,
            date_column=date_column,
            metric=metric,
            aggregation=aggregation,
            interval=time_interval,
            sheet_name=sheet_name,
        )
    elif op_upper == "CORRELATION_MATRIX":
        return calculate_dataset_correlations(file_path, method="PEARSON", sheet_name=sheet_name)
    elif op_upper == "OUTLIER_SUMMARY":
        return detect_dataset_outliers(file_path, sheet_name=sheet_name)
    else:
        return profile_large_dataset(file_path, sheet_name=sheet_name)


# ---------------------------------------------------------------------------
# Tool 4: Statistical Correlations
# ---------------------------------------------------------------------------
@mcp.tool()
def calculate_dataset_correlations(
    file_path: str,
    method: str = "PEARSON",
    columns: list[str] | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Calculates Pearson or Spearman correlations across numeric columns with ranking and noncausality checks."""
    t0 = time.perf_counter()
    loaded = DatasetLoader.load_and_inspect(file_path, sheet_name=sheet_name)
    if loaded["status"] != "SUCCESS":
        return loaded

    schema = loaded["schema"]
    num_cols = columns or schema.get("numeric_columns", [])

    with ManagedDuckDB() as engine:
        source_sql = schema.get("read_sql") or engine.get_csv_read_sql(file_path)
        corr_results = CorrelationEngine.calculate_correlation_matrix(
            duck_engine=engine,
            source_sql=source_sql,
            numeric_columns=num_cols,
            method=method,
        )

    duration_ms = (time.perf_counter() - t0) * 1000

    if corr_results["status"] != "SUCCESS":
        return corr_results

    report = AnalysisReportBuilder.build_report(
        dataset_meta=loaded,
        backend=loaded["backend"],
        correlations=corr_results,
        duration_ms=duration_ms,
        rows_scanned=schema.get("row_count", 0),
    )
    voice_tan, voice_en = ResultFormatter.format_voice_summaries(report)
    markdown = ResultFormatter.format_markdown_report(report)

    report["markdown"] = markdown
    report["voice_tanglish"] = voice_tan
    report["voice_en"] = voice_en
    return report


# ---------------------------------------------------------------------------
# Tool 5: Group Aggregation
# ---------------------------------------------------------------------------
@mcp.tool()
def aggregate_dataset_by_group(
    file_path: str,
    group_by: list[str],
    metric: str,
    aggregation: str = "SUM",
    sort_desc: bool = True,
    limit: int = 50,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Computes group-by aggregations and category percentages using DuckDB SQL."""
    loaded = DatasetLoader.load_and_inspect(file_path, sheet_name=sheet_name)
    if loaded["status"] != "SUCCESS":
        return loaded

    schema = loaded["schema"]
    with ManagedDuckDB() as engine:
        source_sql = schema.get("read_sql") or engine.get_csv_read_sql(file_path)
        res = SegmentAnalytics.aggregate_by_group(
            duck_engine=engine,
            source_sql=source_sql,
            group_by_cols=group_by,
            metric_col=metric,
            agg=aggregation,
            sort_desc=sort_desc,
            limit=limit,
        )
    return res


# ---------------------------------------------------------------------------
# Tool 6: Time Trends
# ---------------------------------------------------------------------------
@mcp.tool()
def analyze_dataset_trends(
    file_path: str,
    date_column: str,
    metric: str,
    aggregation: str = "SUM",
    interval: str = "MONTH",
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Evaluates time-series trends, periodic growth deltas, and trajectory direction."""
    loaded = DatasetLoader.load_and_inspect(file_path, sheet_name=sheet_name)
    if loaded["status"] != "SUCCESS":
        return loaded

    schema = loaded["schema"]
    with ManagedDuckDB() as engine:
        source_sql = schema.get("read_sql") or engine.get_csv_read_sql(file_path)
        res = TrendEngine.analyze_time_trends(
            duck_engine=engine,
            source_sql=source_sql,
            date_col=date_column,
            metric_col=metric,
            agg=aggregation,
            interval=interval,
        )
    return res


# ---------------------------------------------------------------------------
# Tool 7: Outlier Detection
# ---------------------------------------------------------------------------
@mcp.tool()
def detect_dataset_outliers(
    file_path: str,
    columns: list[str] | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Identifies statistical anomalies, IQR boundaries, and negative metric values."""
    loaded = DatasetLoader.load_and_inspect(file_path, sheet_name=sheet_name)
    if loaded["status"] != "SUCCESS":
        return loaded

    schema = loaded["schema"]
    num_cols = columns or schema.get("numeric_columns", [])

    with ManagedDuckDB() as engine:
        source_sql = schema.get("read_sql") or engine.get_csv_read_sql(file_path)
        res = AnomalyEngine.detect_outliers_and_anomalies(
            duck_engine=engine,
            source_sql=source_sql,
            numeric_cols=num_cols,
        )
    return res


# ---------------------------------------------------------------------------
# Tool 8: Segment Comparison
# ---------------------------------------------------------------------------
@mcp.tool()
def compare_dataset_segments(
    file_path: str,
    segment_column: str,
    metric: str,
    aggregation: str = "SUM",
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Compares categorical segments and calculates their contribution to overall metric."""
    return aggregate_dataset_by_group(
        file_path=file_path,
        group_by=[segment_column],
        metric=metric,
        aggregation=aggregation,
        sort_desc=True,
        limit=50,
        sheet_name=sheet_name,
    )


# ---------------------------------------------------------------------------
# Tool 9: Job Status
# ---------------------------------------------------------------------------
@mcp.tool()
def get_dataset_analysis_status(job_id: str) -> dict[str, Any]:
    """Inspects the execution progress and state of an active analysis job."""
    job = job_manager.get_job(job_id)
    if not job:
        return {
            "status": "ERROR",
            "error_code": "JOB_NOT_FOUND",
            "message": f"Analysis job '{job_id}' does not exist.",
        }
    return {
        "status": "SUCCESS",
        "job_id": job.job_id,
        "job_status": job.status,
        "operation": job.operation,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "duration_ms": job.duration_ms,
        "error_message": job.error_message,
    }


# ---------------------------------------------------------------------------
# Tool 10: Cancel Job
# ---------------------------------------------------------------------------
@mcp.tool()
def cancel_dataset_analysis(job_id: str) -> dict[str, Any]:
    """Safely cancels an authorized running analysis job."""
    cancelled = job_manager.cancel_job(job_id)
    if not cancelled:
        return {
            "status": "ERROR",
            "error_code": "JOB_NOT_FOUND",
            "message": f"Could not cancel job '{job_id}': Job not found.",
        }
    return {
        "status": "SUCCESS",
        "job_id": job_id,
        "message": f"Analysis job '{job_id}' cancellation signal recorded.",
    }


# ---------------------------------------------------------------------------
# Tool 11: Full Report Retrieval
# ---------------------------------------------------------------------------
@mcp.tool()
def get_dataset_analysis_report(file_path: str, include_voice: bool = True) -> dict[str, Any]:
    """Retrieves complete verified analysis report for a dataset with markdown and voice scripts."""
    t0 = time.perf_counter()
    loaded = DatasetLoader.load_and_inspect(file_path)
    if loaded["status"] != "SUCCESS":
        return loaded

    schema = loaded["schema"]
    num_cols = schema.get("numeric_columns", [])
    cat_cols = schema.get("categorical_columns", [])
    all_cols = schema.get("column_names", [])

    with ManagedDuckDB() as engine:
        source_sql = schema.get("read_sql") or engine.get_csv_read_sql(file_path)

        num_profiles = SummaryStatistics.profile_numeric_columns(engine, source_sql, num_cols)
        missing_info = SummaryStatistics.analyze_missing_values(engine, source_sql, all_cols)
        dup_info = SummaryStatistics.analyze_duplicate_rows(engine, source_sql)

        corrs = None
        if len(num_cols) >= 2:
            corrs = CorrelationEngine.calculate_correlation_matrix(
                engine, source_sql, num_cols, method="PEARSON"
            )

        outliers = None
        if num_cols:
            outliers = AnomalyEngine.detect_outliers_and_anomalies(engine, source_sql, num_cols)

    duration_ms = (time.perf_counter() - t0) * 1000

    report = AnalysisReportBuilder.build_report(
        dataset_meta=loaded,
        backend=loaded["backend"],
        profile={"missing_values": missing_info, "duplicate_records": dup_info},
        statistics={"numeric_distributions": num_profiles},
        correlations=corrs if corrs and corrs.get("status") == "SUCCESS" else None,
        outliers=outliers,
        duration_ms=duration_ms,
        rows_scanned=schema.get("row_count", 0),
    )

    markdown = ResultFormatter.format_markdown_report(report)
    report["markdown"] = markdown

    if include_voice:
        v_tan, v_en = ResultFormatter.format_voice_summaries(report)
        report["voice_tanglish"] = v_tan
        report["voice_en"] = v_en

    return report


if __name__ == "__main__":
    mcp.run()
