"""
Segment Analytics & Group Aggregation Engine.
Performs scalable SQL-based group-by aggregations and category breakdowns.
"""

from __future__ import annotations

import logging
from typing import Any
import pandas as pd

from zye_computer_intelligence.data_engine.duckdb_engine import ManagedDuckDB
from zye_computer_intelligence.data_engine.query_planner import QueryPlanner

logger = logging.getLogger("zye.computer_intelligence.segment")


class SegmentAnalytics:
    """Executes group aggregation and segment comparisons."""

    @staticmethod
    def aggregate_by_group(
        duck_engine: ManagedDuckDB,
        source_sql: str,
        group_by_cols: list[str],
        metric_col: str,
        agg: str = "SUM",
        sort_desc: bool = True,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Calculates group-by aggregates with totals and share percentages."""
        try:
            sql = QueryPlanner.build_group_aggregate_query(
                source_sql=source_sql,
                group_by_cols=group_by_cols,
                metric_col=metric_col,
                agg=agg,
                sort_desc=sort_desc,
                limit=limit,
            )
            df = duck_engine.query_df(sql, max_rows=limit)
            if df.empty:
                return {
                    "status": "SUCCESS",
                    "group_by": group_by_cols,
                    "metric": metric_col,
                    "aggregation": agg,
                    "total_groups": 0,
                    "segments": [],
                }

            # Calculate total metric sum across returned segments
            total_metric = df["metric_value"].sum()
            segments: list[dict[str, Any]] = []

            for _, row in df.iterrows():
                grp_keys = {col: str(row[col]) for col in group_by_cols}
                val = float(row["metric_value"]) if pd.notna(row["metric_value"]) else 0.0
                cnt = int(row["row_count"])
                pct = round((val / total_metric * 100), 2) if total_metric != 0 else 0.0

                seg_data = {
                    **grp_keys,
                    "value": round(val, 2),
                    "row_count": cnt,
                    "percentage_share": pct,
                }
                segments.append(seg_data)

            return {
                "status": "SUCCESS",
                "group_by": group_by_cols,
                "metric": metric_col,
                "aggregation": agg,
                "total_groups": len(segments),
                "segments": segments,
            }
        except Exception as e:
            logger.error("Group aggregation failed: %s", e)
            return {
                "status": "ERROR",
                "error_code": "GROUP_AGGREGATION_FAILED",
                "message": f"Failed to execute group aggregation: {e}",
            }
