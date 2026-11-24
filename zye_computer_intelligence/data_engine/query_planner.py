"""
Safe Analytical Query Planner.
Generates structured DuckDB SQL queries with strict parameter binding and identifier quoting.
"""

from __future__ import annotations

from typing import Any
from .query_validator import QueryValidator, AGG_SQL_MAP


class QueryPlanner:
    """Constructs safe DuckDB SQL queries from validated analytical parameters."""

    @staticmethod
    def build_row_count_query(source_sql: str) -> str:
        return f"SELECT COUNT(*) AS total_rows FROM ({source_sql}) AS _src;"

    @staticmethod
    def build_group_aggregate_query(
        source_sql: str,
        group_by_cols: list[str],
        metric_col: str,
        agg: str,
        sort_desc: bool = True,
        limit: int = 50,
    ) -> str:
        agg_upper = QueryValidator.validate_aggregation(agg)
        quoted_groups = [QueryValidator.quote_identifier(c) for c in group_by_cols]
        quoted_metric = QueryValidator.quote_identifier(metric_col)

        group_clause = ", ".join(quoted_groups)
        if agg_upper == "COUNT_DISTINCT":
            agg_expr = f"COUNT(DISTINCT {quoted_metric})"
        else:
            sql_agg = AGG_SQL_MAP[agg_upper]
            agg_expr = f"{sql_agg}({quoted_metric})"

        sort_dir = "DESC" if sort_desc else "ASC"
        limit_val = min(max(1, int(limit)), 100_000)

        sql = f"""
        SELECT
            {group_clause},
            {agg_expr} AS metric_value,
            COUNT(*) AS row_count
        FROM ({source_sql}) AS _src
        WHERE {quoted_metric} IS NOT NULL
        GROUP BY {group_clause}
        ORDER BY metric_value {sort_dir} NULLS LAST
        LIMIT {limit_val};
        """
        return sql.strip()

    @staticmethod
    def build_time_trend_query(
        source_sql: str,
        date_col: str,
        metric_col: str,
        agg: str = "SUM",
        interval: str = "MONTH",
    ) -> str:
        agg_upper = QueryValidator.validate_aggregation(agg)
        quoted_date = QueryValidator.quote_identifier(date_col)
        quoted_metric = QueryValidator.quote_identifier(metric_col)

        interval_clean = interval.strip().upper()
        if interval_clean not in ("DAY", "WEEK", "MONTH", "YEAR"):
            interval_clean = "MONTH"

        if agg_upper == "COUNT_DISTINCT":
            agg_expr = f"COUNT(DISTINCT {quoted_metric})"
        else:
            sql_agg = AGG_SQL_MAP[agg_upper]
            agg_expr = f"{sql_agg}({quoted_metric})"

        sql = f"""
        SELECT
            DATE_TRUNC('{interval_clean.lower()}', CAST({quoted_date} AS DATE)) AS period,
            {agg_expr} AS metric_value,
            COUNT(*) AS period_count
        FROM ({source_sql}) AS _src
        WHERE {quoted_date} IS NOT NULL AND {quoted_metric} IS NOT NULL
        GROUP BY 1
        ORDER BY period ASC;
        """
        return sql.strip()

    @staticmethod
    def build_missing_values_query(source_sql: str, columns: list[str]) -> str:
        select_parts: list[str] = ["COUNT(*) AS _total_count"]
        for c in columns:
            q = QueryValidator.quote_identifier(c)
            # Count nulls and empty strings
            select_parts.append(
                f"COUNT(CASE WHEN {q} IS NULL THEN 1 END) AS {QueryValidator.quote_identifier('null_' + c)}"
            )
            select_parts.append(
                f"COUNT(CASE WHEN TRIM(CAST({q} AS VARCHAR)) = '' THEN 1 END) AS {QueryValidator.quote_identifier('empty_' + c)}"
            )

        sql = f"SELECT {', '.join(select_parts)} FROM ({source_sql}) AS _src;"
        return sql.strip()

    @staticmethod
    def build_duplicate_count_query(source_sql: str, key_columns: list[str] | None = None) -> str:
        if key_columns:
            quoted_keys = [QueryValidator.quote_identifier(k) for k in key_columns]
            cols = ", ".join(quoted_keys)
            sql = f"""
            SELECT COUNT(*) AS duplicate_groups, SUM(group_size - 1) AS duplicate_rows
            FROM (
                SELECT {cols}, COUNT(*) AS group_size
                FROM ({source_sql}) AS _src
                GROUP BY {cols}
                HAVING COUNT(*) > 1
            ) AS _dups;
            """
        else:
            sql = f"""
            SELECT COUNT(*) AS duplicate_groups, SUM(group_size - 1) AS duplicate_rows
            FROM (
                SELECT *, COUNT(*) AS group_size
                FROM ({source_sql}) AS _src
                GROUP BY ALL
                HAVING COUNT(*) > 1
            ) AS _dups;
            """
        return sql.strip()

    @staticmethod
    def build_numeric_profile_query(source_sql: str, numeric_cols: list[str]) -> str:
        select_exprs: list[str] = ["COUNT(*) AS total_rows"]
        for col in numeric_cols:
            q = QueryValidator.quote_identifier(col)
            alias = col.replace('"', '')
            select_exprs.extend([
                f"COUNT({q}) AS {QueryValidator.quote_identifier(alias + '__count')}",
                f"COUNT(CASE WHEN {q} IS NULL THEN 1 END) AS {QueryValidator.quote_identifier(alias + '__nulls')}",
                f"AVG({q}) AS {QueryValidator.quote_identifier(alias + '__mean')}",
                f"MEDIAN({q}) AS {QueryValidator.quote_identifier(alias + '__median')}",
                f"STDDEV_SAMP({q}) AS {QueryValidator.quote_identifier(alias + '__std')}",
                f"MIN({q}) AS {QueryValidator.quote_identifier(alias + '__min')}",
                f"MAX({q}) AS {QueryValidator.quote_identifier(alias + '__max')}",
                f"QUANTILE_CONT({q}, 0.25) AS {QueryValidator.quote_identifier(alias + '__p25')}",
                f"QUANTILE_CONT({q}, 0.75) AS {QueryValidator.quote_identifier(alias + '__p75')}",
            ])
        sql = f"SELECT {', '.join(select_exprs)} FROM ({source_sql}) AS _src;"
        return sql.strip()
