"""
SQL & Analytical Query Validator.
Enforces operation allowlists, validates column names against schemas, and prevents SQL injection.
"""

from __future__ import annotations

import re
from typing import Any

ALLOWED_OPERATIONS = {
    "DATASET_PROFILE",
    "DESCRIBE_SCHEMA",
    "ROW_COUNT",
    "COLUMN_SUMMARY",
    "FILTER_ROWS",
    "GROUP_AGGREGATE",
    "TOP_N",
    "BOTTOM_N",
    "TIME_TREND",
    "CORRELATION_MATRIX",
    "PAIRWISE_CORRELATION",
    "MISSING_VALUE_ANALYSIS",
    "DUPLICATE_ROW_COUNT",
    "OUTLIER_SUMMARY",
    "SEGMENT_COMPARISON",
}

DISALLOWED_SQL_KEYWORDS = {
    "CREATE", "DROP", "ALTER", "DELETE", "UPDATE", "INSERT",
    "ATTACH", "DETACH", "COPY", "INSTALL", "LOAD", "PRAGMA",
    "EXPORT", "IMPORT", "TRUNCATE", "REPLACE", "EXEC", "EXECUTE",
}

ALLOWED_AGGREGATIONS = {
    "SUM", "AVG", "MEAN", "COUNT", "MIN", "MAX",
    "MEDIAN", "STDDEV", "VARIANCE", "COUNT_DISTINCT",
}

AGG_SQL_MAP = {
    "SUM": "SUM",
    "AVG": "AVG",
    "MEAN": "AVG",
    "COUNT": "COUNT",
    "MIN": "MIN",
    "MAX": "MAX",
    "MEDIAN": "MEDIAN",
    "STDDEV": "STDDEV_SAMP",
    "VARIANCE": "VAR_SAMP",
    "COUNT_DISTINCT": "COUNT(DISTINCT",
}


class QueryValidator:
    """Validates analytical query requests before SQL generation."""

    @staticmethod
    def quote_identifier(col: str) -> str:
        """Safely quotes a column or table identifier in DuckDB SQL."""
        sanitized = str(col).replace('"', '""')
        return f'"{sanitized}"'

    @staticmethod
    def validate_operation(operation: str) -> str:
        """Validates that the requested analytical operation is on the allowlist."""
        op_upper = str(operation).strip().upper()
        if op_upper not in ALLOWED_OPERATIONS:
            raise ValueError(
                f"Unsupported analytical operation '{operation}'. Allowed: {sorted(ALLOWED_OPERATIONS)}"
            )
        return op_upper

    @staticmethod
    def validate_columns_exist(columns: list[str], available_columns: list[str]) -> list[str]:
        """Ensures all requested columns exist in the dataset."""
        avail_lower = {c.lower(): c for c in available_columns}
        validated: list[str] = []
        for c in columns:
            c_clean = str(c).strip()
            if c_clean.lower() in avail_lower:
                validated.append(avail_lower[c_clean.lower()])
            else:
                raise ValueError(
                    f"Column '{c}' not found in dataset. Available columns: {available_columns}"
                )
        return validated

    @staticmethod
    def validate_aggregation(agg: str) -> str:
        """Validates and normalizes aggregation function name."""
        agg_upper = str(agg).strip().upper()
        if agg_upper not in ALLOWED_AGGREGATIONS:
            raise ValueError(
                f"Unsupported aggregation '{agg}'. Supported: {sorted(ALLOWED_AGGREGATIONS)}"
            )
        return agg_upper

    @staticmethod
    def sanitize_raw_sql_check(sql_fragment: str) -> None:
        """Scans arbitrary strings for dangerous SQL DDL/DML injection keywords."""
        tokens = re.findall(r"\b[A-Za-z_]+\b", sql_fragment.upper())
        for token in tokens:
            if token in DISALLOWED_SQL_KEYWORDS:
                raise SecurityError(
                    f"Security restriction: Keyword '{token}' is prohibited in analytical queries."
                )


class SecurityError(Exception):
    """Raised when an operation violates query security rules."""
    pass
