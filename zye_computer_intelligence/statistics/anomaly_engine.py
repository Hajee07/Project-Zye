"""
Statistical Anomaly & Outlier Detection Engine.
Calculates IQR boundaries, extreme distribution deviations, and negative metric anomalies.
"""

from __future__ import annotations

import logging
from typing import Any
import pandas as pd

from zye_computer_intelligence.data_engine.duckdb_engine import ManagedDuckDB
from zye_computer_intelligence.data_engine.query_validator import QueryValidator

logger = logging.getLogger("zye.computer_intelligence.anomaly")


class AnomalyEngine:
    """Detects statistical outliers, IQR bound violations, and negative anomalies."""

    @staticmethod
    def detect_outliers_and_anomalies(
        duck_engine: ManagedDuckDB,
        source_sql: str,
        numeric_cols: list[str],
    ) -> dict[str, Any]:
        """Calculates IQR outlier counts, bounds, and negative values for numeric columns."""
        anomalies_by_column: dict[str, dict[str, Any]] = {}
        columns_with_anomalies: list[str] = []

        for col in numeric_cols:
            q = QueryValidator.quote_identifier(col)
            try:
                # 1. Calculate Quartiles and min
                stats_sql = f"""
                SELECT
                    COUNT({q}) AS val_count,
                    MIN(CAST({q} AS DOUBLE)) AS min_val,
                    QUANTILE_CONT(CAST({q} AS DOUBLE), 0.25) AS q1,
                    QUANTILE_CONT(CAST({q} AS DOUBLE), 0.75) AS q3
                FROM ({source_sql}) AS _src
                WHERE {q} IS NOT NULL;
                """
                res = duck_engine.query_df(stats_sql)
                if res.empty or pd.isna(res["q1"].iloc[0]) or pd.isna(res["q3"].iloc[0]):
                    continue

                val_count = int(res["val_count"].iloc[0])
                min_val = float(res["min_val"].iloc[0])
                q1 = float(res["q1"].iloc[0])
                q3 = float(res["q3"].iloc[0])
                iqr = q3 - q1

                if val_count < 4 or iqr == 0:
                    # Not enough variance or samples for IQR bounds
                    continue

                lower_bound = round(q1 - (1.5 * iqr), 4)
                upper_bound = round(q3 + (1.5 * iqr), 4)

                # Count outliers outside [lower_bound, upper_bound]
                outlier_sql = f"""
                SELECT
                    COUNT(CASE WHEN CAST({q} AS DOUBLE) < {lower_bound} OR CAST({q} AS DOUBLE) > {upper_bound} THEN 1 END) AS outlier_count,
                    COUNT(CASE WHEN CAST({q} AS DOUBLE) < 0 THEN 1 END) AS negative_count
                FROM ({source_sql}) AS _src
                WHERE {q} IS NOT NULL;
                """
                o_df = duck_engine.query_df(outlier_sql)
                outlier_count = int(o_df["outlier_count"].iloc[0]) if not o_df.empty else 0
                negative_count = int(o_df["negative_count"].iloc[0]) if not o_df.empty else 0

                has_anomaly = (outlier_count > 0) or (negative_count > 0 and min_val < 0)
                if has_anomaly:
                    columns_with_anomalies.append(col)

                anomalies_by_column[col] = {
                    "total_valid_samples": val_count,
                    "q1": q1,
                    "q3": q3,
                    "iqr": iqr,
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                    "outlier_count": outlier_count,
                    "outlier_pct": round((outlier_count / val_count * 100), 2) if val_count > 0 else 0.0,
                    "negative_count": negative_count,
                    "has_negative_values": negative_count > 0,
                }
            except Exception as e:
                logger.error("Outlier detection failed for column %s: %s", col, e)

        return {
            "status": "SUCCESS",
            "columns_analyzed": numeric_cols,
            "columns_with_anomalies": columns_with_anomalies,
            "anomalies_by_column": anomalies_by_column,
            "has_anomalies": len(columns_with_anomalies) > 0,
        }
