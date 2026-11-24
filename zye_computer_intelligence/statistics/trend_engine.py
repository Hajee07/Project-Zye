"""
Time Trend & Chronological Aggregation Engine.
Aggregates time-series metrics by day, week, month, or year and evaluates trend direction.
"""

from __future__ import annotations

import logging
from typing import Any
import pandas as pd

from zye_computer_intelligence.data_engine.duckdb_engine import ManagedDuckDB
from zye_computer_intelligence.data_engine.query_planner import QueryPlanner

logger = logging.getLogger("zye.computer_intelligence.trend")


class TrendEngine:
    """Evaluates chronological trajectories and period-over-period movements."""

    @staticmethod
    def analyze_time_trends(
        duck_engine: ManagedDuckDB,
        source_sql: str,
        date_col: str,
        metric_col: str,
        agg: str = "SUM",
        interval: str = "MONTH",
    ) -> dict[str, Any]:
        """Calculates time trends, periodic deltas, and overall growth direction."""
        try:
            sql = QueryPlanner.build_time_trend_query(
                source_sql=source_sql,
                date_col=date_col,
                metric_col=metric_col,
                agg=agg,
                interval=interval,
            )
            df = duck_engine.query_df(sql, max_rows=1000)
            if df.empty:
                return {
                    "status": "SUCCESS",
                    "date_column": date_col,
                    "metric_column": metric_col,
                    "interval": interval,
                    "trend_direction": "INSUFFICIENT_DATA",
                    "periods": [],
                }

            periods: list[dict[str, Any]] = []
            values: list[float] = []

            prev_val = None
            for _, row in df.iterrows():
                period_str = str(row["period"]).split(" ")[0]
                val = float(row["metric_value"]) if pd.notna(row["metric_value"]) else 0.0
                cnt = int(row["period_count"])
                values.append(val)

                delta = round(val - prev_val, 2) if prev_val is not None else None
                pct_chg = round((delta / prev_val * 100), 2) if prev_val is not None and prev_val != 0 else None

                periods.append({
                    "period": period_str,
                    "value": round(val, 2),
                    "count": cnt,
                    "delta": delta,
                    "pct_change": pct_chg,
                })
                prev_val = val

            # Detect trajectory
            if len(values) >= 2:
                first_half_avg = sum(values[:len(values)//2]) / max(1, len(values)//2)
                second_half_avg = sum(values[len(values)//2:]) / max(1, len(values) - len(values)//2)
                if second_half_avg > first_half_avg * 1.05:
                    direction = "GROWING"
                elif second_half_avg < first_half_avg * 0.95:
                    direction = "DECLINING"
                else:
                    direction = "STABLE"
            else:
                direction = "SINGLE_PERIOD"

            return {
                "status": "SUCCESS",
                "date_column": date_col,
                "metric_column": metric_col,
                "interval": interval,
                "total_periods": len(periods),
                "trend_direction": direction,
                "periods": periods,
            }
        except Exception as e:
            logger.error("Trend analysis failed: %s", e)
            return {
                "status": "ERROR",
                "error_code": "TREND_ANALYSIS_FAILED",
                "message": f"Failed to compute time trends: {e}",
            }
