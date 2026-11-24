"""
Summary Statistics, Profiling, Missing-Value & Duplicate-Row Engine.
Computes deterministic descriptive statistics, percentiles, and data-quality diagnostics.
"""

from __future__ import annotations

import logging
from typing import Any
import pandas as pd

from zye_computer_intelligence.data_engine.duckdb_engine import ManagedDuckDB
from zye_computer_intelligence.data_engine.query_validator import QueryValidator

logger = logging.getLogger("zye.computer_intelligence.statistics")


class SummaryStatistics:
    """Calculates comprehensive dataset statistics and quality profiles."""

    @staticmethod
    def profile_numeric_columns(
        duck_engine: ManagedDuckDB,
        source_sql: str,
        numeric_cols: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Calculates count, nulls, mean, median, std, min, max, p25, p75, IQR for numeric columns."""
        if not numeric_cols:
            return {}

        profiles: dict[str, dict[str, Any]] = {}
        for col in numeric_cols:
            q = QueryValidator.quote_identifier(col)
            sql = f"""
            SELECT
                COUNT({q}) AS val_count,
                COUNT(CASE WHEN {q} IS NULL THEN 1 END) AS null_count,
                AVG(CAST({q} AS DOUBLE)) AS mean_val,
                MEDIAN(CAST({q} AS DOUBLE)) AS median_val,
                STDDEV_SAMP(CAST({q} AS DOUBLE)) AS std_val,
                MIN(CAST({q} AS DOUBLE)) AS min_val,
                MAX(CAST({q} AS DOUBLE)) AS max_val,
                QUANTILE_CONT(CAST({q} AS DOUBLE), 0.25) AS p25,
                QUANTILE_CONT(CAST({q} AS DOUBLE), 0.75) AS p75
            FROM ({source_sql}) AS _src;
            """
            try:
                res_df = duck_engine.query_df(sql)
                if not res_df.empty:
                    row = res_df.iloc[0]
                    val_count = int(row["val_count"])
                    null_count = int(row["null_count"])
                    total = val_count + null_count
                    mean_val = round(float(row["mean_val"]), 4) if pd.notna(row["mean_val"]) else None
                    median_val = round(float(row["median_val"]), 4) if pd.notna(row["median_val"]) else None
                    std_val = round(float(row["std_val"]), 4) if pd.notna(row["std_val"]) else None
                    min_val = round(float(row["min_val"]), 4) if pd.notna(row["min_val"]) else None
                    max_val = round(float(row["max_val"]), 4) if pd.notna(row["max_val"]) else None
                    p25 = round(float(row["p25"]), 4) if pd.notna(row["p25"]) else None
                    p75 = round(float(row["p75"]), 4) if pd.notna(row["p75"]) else None
                    iqr = round(p75 - p25, 4) if p25 is not None and p75 is not None else None

                    profiles[col] = {
                        "count": val_count,
                        "null_count": null_count,
                        "null_pct": round((null_count / total * 100), 2) if total > 0 else 0.0,
                        "mean": mean_val,
                        "median": median_val,
                        "std_dev": std_val,
                        "min": min_val,
                        "max": max_val,
                        "p25": p25,
                        "p75": p75,
                        "iqr": iqr,
                    }
            except Exception as e:
                logger.error("Numeric profiling failed for column '%s': %s", col, e)
                profiles[col] = {"error": str(e)}

        return profiles

    @staticmethod
    def profile_categorical_columns(
        duck_engine: ManagedDuckDB,
        source_sql: str,
        cat_cols: list[str],
        top_n: int = 5,
    ) -> dict[str, dict[str, Any]]:
        """Calculates count, distinct count, null count, and top frequent categories."""
        if not cat_cols:
            return {}

        profiles: dict[str, dict[str, Any]] = {}
        for col in cat_cols[:10]:  # Bound to first 10 categorical columns
            q = QueryValidator.quote_identifier(col)
            try:
                # 1. Distinct & null count
                meta_sql = f"""
                SELECT
                    COUNT({q}) AS val_count,
                    COUNT(DISTINCT {q}) AS distinct_count,
                    COUNT(CASE WHEN {q} IS NULL THEN 1 END) AS null_count
                FROM ({source_sql}) AS _src;
                """
                m_df = duck_engine.query_df(meta_sql)
                if m_df.empty:
                    continue
                m_row = m_df.iloc[0]
                val_count = int(m_row["val_count"])
                distinct_count = int(m_row["distinct_count"])
                null_count = int(m_row["null_count"])

                # 2. Top N values
                top_sql = f"""
                SELECT CAST({q} AS VARCHAR) AS cat_val, COUNT(*) AS freq
                FROM ({source_sql}) AS _src
                WHERE {q} IS NOT NULL
                GROUP BY 1
                ORDER BY freq DESC
                LIMIT {top_n};
                """
                t_df = duck_engine.query_df(top_sql)
                top_values = [
                    {"value": str(r["cat_val"]), "count": int(r["freq"])}
                    for _, r in t_df.iterrows()
                ]

                profiles[col] = {
                    "count": val_count,
                    "distinct_count": distinct_count,
                    "null_count": null_count,
                    "top_categories": top_values,
                }
            except Exception as e:
                logger.error("Categorical profiling failed for column '%s': %s", col, e)
                profiles[col] = {"error": str(e)}

        return profiles

    @staticmethod
    def analyze_missing_values(
        duck_engine: ManagedDuckDB,
        source_sql: str,
        columns: list[str],
    ) -> dict[str, Any]:
        """Calculates exact missing value metrics (NULL vs empty string) per column."""
        total_rows_df = duck_engine.query_df(f"SELECT COUNT(*) AS total FROM ({source_sql}) AS _src;")
        total_rows = int(total_rows_df["total"].iloc[0]) if not total_rows_df.empty else 0

        if total_rows == 0:
            return {
                "total_rows": 0,
                "missing_by_column": {},
                "columns_with_missing": [],
                "has_missing": False,
            }

        missing_by_column: dict[str, dict[str, Any]] = {}
        cols_with_missing: list[str] = []

        for col in columns:
            q = QueryValidator.quote_identifier(col)
            sql = f"""
            SELECT
                COUNT(CASE WHEN {q} IS NULL THEN 1 END) AS null_cnt,
                COUNT(CASE WHEN TRIM(CAST({q} AS VARCHAR)) = '' THEN 1 END) AS empty_cnt
            FROM ({source_sql}) AS _src;
            """
            try:
                res = duck_engine.query_df(sql)
                if not res.empty:
                    null_cnt = int(res["null_cnt"].iloc[0])
                    empty_cnt = int(res["empty_cnt"].iloc[0])
                    total_missing = null_cnt + empty_cnt
                    pct = round((total_missing / total_rows) * 100, 2)

                    missing_by_column[col] = {
                        "null_count": null_cnt,
                        "empty_string_count": empty_cnt,
                        "total_missing": total_missing,
                        "missing_percentage": pct,
                    }
                    if total_missing > 0:
                        cols_with_missing.append(col)
            except Exception as e:
                logger.debug("Missing value inspection error on %s: %s", col, e)

        return {
            "total_rows": total_rows,
            "missing_by_column": missing_by_column,
            "columns_with_missing": cols_with_missing,
            "has_missing": len(cols_with_missing) > 0,
        }

    @staticmethod
    def analyze_duplicate_rows(
        duck_engine: ManagedDuckDB,
        source_sql: str,
        key_columns: list[str] | None = None,
    ) -> dict[str, Any]:
        """Identifies duplicate row records and duplicate groups."""
        try:
            if key_columns:
                quoted = [QueryValidator.quote_identifier(c) for c in key_columns]
                col_clause = ", ".join(quoted)
                sql = f"""
                SELECT COUNT(*) AS dup_groups, COALESCE(SUM(grp_size - 1), 0) AS dup_rows
                FROM (
                    SELECT {col_clause}, COUNT(*) AS grp_size
                    FROM ({source_sql}) AS _src
                    GROUP BY {col_clause}
                    HAVING COUNT(*) > 1
                ) AS _d;
                """
            else:
                sql = f"""
                SELECT COUNT(*) AS dup_groups, COALESCE(SUM(grp_size - 1), 0) AS dup_rows
                FROM (
                    SELECT *, COUNT(*) AS grp_size
                    FROM ({source_sql}) AS _src
                    GROUP BY ALL
                    HAVING COUNT(*) > 1
                ) AS _d;
                """
            res_df = duck_engine.query_df(sql)
            if not res_df.empty:
                dup_groups = int(res_df["dup_groups"].iloc[0])
                dup_rows = int(res_df["dup_rows"].iloc[0])
            else:
                dup_groups = 0
                dup_rows = 0

            return {
                "duplicate_groups": dup_groups,
                "duplicate_rows": dup_rows,
                "has_duplicates": dup_rows > 0,
                "key_columns_used": key_columns or ["ALL_COLUMNS"],
            }
        except Exception as e:
            logger.error("Duplicate analysis failed: %s", e)
            return {
                "duplicate_groups": 0,
                "duplicate_rows": 0,
                "has_duplicates": False,
                "error": str(e),
            }
