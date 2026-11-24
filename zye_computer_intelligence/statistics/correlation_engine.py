"""
Statistical Correlation Engine (Pearson & Spearman).
Computes pairwise correlations, full matrices, relationship rankings, and noncausality explanations.
"""

from __future__ import annotations

import logging
import math
from typing import Any
import numpy as np
import pandas as pd

from zye_computer_intelligence.data_engine.duckdb_engine import ManagedDuckDB
from zye_computer_intelligence.data_engine.query_validator import QueryValidator

logger = logging.getLogger("zye.computer_intelligence.correlation")


class CorrelationEngine:
    """Calculates, ranks, and interprets statistical correlations."""

    NONCAUSALITY_WARNING = (
        "Statistical correlation does not imply causation. These coefficients describe observed "
        "linear or monotonic association within the dataset, not underlying causal mechanisms. "
        "Confounding variables and data collection artifacts may influence observed relationships."
    )

    @staticmethod
    def classify_association(r: float) -> str:
        """Classifies correlation coefficient strength and direction."""
        if math.isnan(r) or r is None:
            return "UNDEFINED"
        if r >= 0.7:
            return "STRONG_POSITIVE"
        elif r >= 0.4:
            return "MODERATE_POSITIVE"
        elif r >= 0.15:
            return "WEAK_POSITIVE"
        elif r > -0.15:
            return "NEAR_ZERO"
        elif r > -0.4:
            return "WEAK_NEGATIVE"
        elif r > -0.7:
            return "MODERATE_NEGATIVE"
        else:
            return "STRONG_NEGATIVE"

    @classmethod
    def calculate_pairwise_correlation(
        cls,
        duck_engine: ManagedDuckDB,
        source_sql: str,
        col_a: str,
        col_b: str,
        method: str = "PEARSON",
    ) -> dict[str, Any]:
        """Computes correlation between two columns using DuckDB."""
        qa = QueryValidator.quote_identifier(col_a)
        qb = QueryValidator.quote_identifier(col_b)
        method_upper = method.strip().upper()

        warnings: list[str] = []

        try:
            if method_upper == "SPEARMAN":
                # Compute rank correlation in DuckDB
                sql = f"""
                WITH filtered AS (
                    SELECT CAST({qa} AS DOUBLE) AS a, CAST({qb} AS DOUBLE) AS b
                    FROM ({source_sql}) AS _src
                    WHERE {qa} IS NOT NULL AND {qb} IS NOT NULL
                ),
                ranked AS (
                    SELECT
                        RANK() OVER (ORDER BY a) AS r_a,
                        RANK() OVER (ORDER BY b) AS r_b
                    FROM filtered
                )
                SELECT
                    corr(r_a, r_b) AS coef,
                    COUNT(*) AS valid_pairs,
                    STDDEV_SAMP(r_a) AS std_a,
                    STDDEV_SAMP(r_b) AS std_b
                FROM ranked;
                """
            else:
                # Pearson correlation
                sql = f"""
                WITH filtered AS (
                    SELECT CAST({qa} AS DOUBLE) AS a, CAST({qb} AS DOUBLE) AS b
                    FROM ({source_sql}) AS _src
                    WHERE {qa} IS NOT NULL AND {qb} IS NOT NULL
                )
                SELECT
                    corr(a, b) AS coef,
                    COUNT(*) AS valid_pairs,
                    STDDEV_SAMP(a) AS std_a,
                    STDDEV_SAMP(b) AS std_b
                FROM filtered;
                """

            res_df = duck_engine.query_df(sql)
            if res_df.empty:
                return {
                    "column_a": col_a,
                    "column_b": col_b,
                    "method": method_upper,
                    "correlation": None,
                    "valid_pairs": 0,
                    "interpretation": "UNDEFINED",
                    "warnings": ["Dataset has zero valid pairs."],
                }

            row = res_df.iloc[0]
            valid_pairs = int(row["valid_pairs"])
            raw_coef = row["coef"]
            std_a = row["std_a"]
            std_b = row["std_b"]

            if valid_pairs < 3:
                warnings.append("Insufficient sample size (fewer than 3 valid paired observations).")

            if std_a == 0 or std_b == 0 or (std_a is not None and math.isnan(std_a)) or (std_b is not None and math.isnan(std_b)):
                warnings.append("One or both columns have zero variance (constant values). Correlation is undefined.")
                return {
                    "column_a": col_a,
                    "column_b": col_b,
                    "method": method_upper,
                    "correlation": None,
                    "valid_pairs": valid_pairs,
                    "interpretation": "CONSTANT_COLUMN_ZERO_VARIANCE",
                    "warnings": warnings,
                }

            if raw_coef is None or (isinstance(raw_coef, float) and math.isnan(raw_coef)):
                coef = None
                interp = "UNDEFINED"
            else:
                coef = round(float(raw_coef), 4)
                # Clamp within [-1.0, 1.0] due to floating precision
                coef = max(-1.0, min(1.0, coef))
                interp = cls.classify_association(coef)

            return {
                "column_a": col_a,
                "column_b": col_b,
                "method": method_upper,
                "correlation": coef,
                "valid_pairs": valid_pairs,
                "interpretation": interp,
                "warnings": warnings,
            }
        except Exception as e:
            logger.error("Pairwise correlation failed between %s and %s: %s", col_a, col_b, e)
            return {
                "column_a": col_a,
                "column_b": col_b,
                "method": method_upper,
                "correlation": None,
                "valid_pairs": 0,
                "interpretation": "ERROR",
                "warnings": [f"Calculation error: {e}"],
            }

    @classmethod
    def calculate_correlation_matrix(
        cls,
        duck_engine: ManagedDuckDB,
        source_sql: str,
        numeric_columns: list[str],
        method: str = "PEARSON",
        max_columns: int = 15,
    ) -> dict[str, Any]:
        """Calculates full pairwise correlation matrix across eligible numeric columns."""
        cols = numeric_columns[:max_columns]
        if len(cols) < 2:
            return {
                "status": "ERROR",
                "error_code": "INSUFFICIENT_NUMERIC_COLUMNS",
                "message": f"At least 2 numeric columns are required for correlation analysis. Found: {cols}",
            }

        pairwise_results: list[dict[str, Any]] = []
        matrix: dict[str, dict[str, float | None]] = {c: {} for c in cols}

        # Diagonal
        for c in cols:
            matrix[c][c] = 1.0

        all_warnings: list[str] = [cls.NONCAUSALITY_WARNING]

        # Calculate off-diagonal pairs
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                col_a = cols[i]
                col_b = cols[j]
                res = cls.calculate_pairwise_correlation(duck_engine, source_sql, col_a, col_b, method=method)
                coef = res["correlation"]
                matrix[col_a][col_b] = coef
                matrix[col_b][col_a] = coef
                pairwise_results.append(res)
                for w in res.get("warnings", []):
                    if w not in all_warnings:
                        all_warnings.append(w)

        # Rank relationships by absolute strength
        valid_pairs = [p for p in pairwise_results if p["correlation"] is not None]
        ranked_pairs = sorted(valid_pairs, key=lambda x: abs(x["correlation"]), reverse=True)

        strong_positive = [p for p in ranked_pairs if p["correlation"] >= 0.7]
        strong_negative = [p for p in ranked_pairs if p["correlation"] <= -0.7]
        moderate_pairs = [p for p in ranked_pairs if 0.4 <= abs(p["correlation"]) < 0.7]

        return {
            "status": "SUCCESS",
            "method": method.upper(),
            "columns": cols,
            "matrix": matrix,
            "pairwise_results": pairwise_results,
            "ranked_relationships": ranked_pairs,
            "strong_positive_correlations": strong_positive,
            "strong_negative_correlations": strong_negative,
            "moderate_correlations": moderate_pairs,
            "noncausality_statement": cls.NONCAUSALITY_WARNING,
            "warnings": all_warnings,
        }
