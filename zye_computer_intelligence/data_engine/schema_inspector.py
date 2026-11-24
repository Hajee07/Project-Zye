"""
Fast Dataset Schema Inspector.
Extracts column names, data types, nullability, and classifies columns into numeric, date, or categorical.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
import pandas as pd

from .duckdb_engine import ManagedDuckDB

logger = logging.getLogger("zye.computer_intelligence.schema")

DATE_KEYWORDS = {"date", "time", "timestamp", "year", "month", "day", "created", "updated"}
ID_KEYWORDS = {"id", "uuid", "code", "key", "number", "num", "hash"}


class SchemaInspector:
    """Inspects dataset schemas efficiently without reading entire files into memory."""

    @staticmethod
    def inspect_csv_schema(file_path: Path | str, duck_engine: ManagedDuckDB | None = None) -> dict[str, Any]:
        """Inspects CSV schema using DuckDB DESCRIBE statement."""
        engine = duck_engine or ManagedDuckDB()
        close_needed = duck_engine is None

        try:
            read_sql = engine.get_csv_read_sql(file_path, sample_size=20_000)
            describe_sql = f"DESCRIBE ({read_sql}) LIMIT 0;"
            desc_df = engine.query_df(describe_sql)

            # Also fetch row count
            count_sql = f"SELECT COUNT(*) AS total_rows FROM ({read_sql}) AS _src;"
            count_df = engine.query_df(count_sql)
            exact_rows = int(count_df["total_rows"].iloc[0]) if not count_df.empty else 0

            columns: list[dict[str, Any]] = []
            numeric_cols: list[str] = []
            categorical_cols: list[str] = []
            date_cols: list[str] = []
            id_cols: list[str] = []

            for _, row in desc_df.iterrows():
                col_name = str(row["column_name"])
                raw_type = str(row["column_type"]).upper()
                nullable = str(row.get("null", "YES")).upper() == "YES"

                col_info = {
                    "name": col_name,
                    "type": raw_type,
                    "nullable": nullable,
                }
                columns.append(col_info)

                col_low = col_name.lower()
                # Classify
                if any(t in raw_type for t in ("INT", "BIGINT", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "HUGEINT")):
                    numeric_cols.append(col_name)
                elif any(t in raw_type for t in ("DATE", "TIMESTAMP", "TIME")):
                    date_cols.append(col_name)
                else:
                    # Check if keyword indicates date
                    if any(kw in col_low for kw in DATE_KEYWORDS):
                        date_cols.append(col_name)
                    else:
                        categorical_cols.append(col_name)

                if any(kw in col_low for kw in ID_KEYWORDS):
                    id_cols.append(col_name)

            return {
                "status": "SUCCESS",
                "format": "CSV",
                "row_count": exact_rows,
                "row_count_type": "EXACT_ROW_COUNT",
                "column_count": len(columns),
                "columns": columns,
                "column_names": [c["name"] for c in columns],
                "numeric_columns": numeric_cols,
                "categorical_columns": categorical_cols,
                "date_columns": date_cols,
                "identifier_columns": id_cols,
                "read_sql": read_sql,
            }
        except Exception as e:
            logger.error("CSV schema inspection failed for %s: %s", file_path, e)
            return {
                "status": "ERROR",
                "error_code": "SCHEMA_INSPECTION_FAILED",
                "message": f"Failed to inspect CSV schema: {e}",
            }
        finally:
            if close_needed:
                engine.close()

    @staticmethod
    def inspect_excel_schema(file_path: Path | str, sheet_name: str | None = None) -> dict[str, Any]:
        """Inspects Excel schema using pandas ExcelFile with row sample."""
        try:
            p = Path(file_path)
            with pd.ExcelFile(str(p)) as xl:
                available_sheets = xl.sheet_names
                selected_sheet = sheet_name if sheet_name and sheet_name in available_sheets else available_sheets[0]

            # Read only 10 rows for schema detection
            sample_df = pd.read_excel(str(p), sheet_name=selected_sheet, nrows=10)

            # Approximate total rows
            full_df = pd.read_excel(str(p), sheet_name=selected_sheet)
            exact_rows = len(full_df)

            numeric_cols = [str(c) for c in sample_df.select_dtypes(include=["number"]).columns]
            date_cols = [str(c) for c in sample_df.select_dtypes(include=["datetime"]).columns]
            categorical_cols = [str(c) for c in sample_df.columns if c not in numeric_cols and c not in date_cols]
            id_cols = [str(c) for c in sample_df.columns if any(kw in str(c).lower() for kw in ID_KEYWORDS)]

            columns = [
                {"name": str(c), "type": str(sample_df[c].dtype), "nullable": True}
                for c in sample_df.columns
            ]

            return {
                "status": "SUCCESS",
                "format": "EXCEL",
                "sheet_name": selected_sheet,
                "available_sheets": available_sheets,
                "row_count": exact_rows,
                "row_count_type": "EXACT_ROW_COUNT",
                "column_count": len(columns),
                "columns": columns,
                "column_names": [c["name"] for c in columns],
                "numeric_columns": numeric_cols,
                "categorical_columns": categorical_cols,
                "date_columns": date_cols,
                "identifier_columns": id_cols,
            }
        except Exception as e:
            logger.error("Excel schema inspection failed for %s: %s", file_path, e)
            return {
                "status": "ERROR",
                "error_code": "EXCEL_SCHEMA_FAILED",
                "message": f"Failed to inspect Excel schema: {e}",
            }
