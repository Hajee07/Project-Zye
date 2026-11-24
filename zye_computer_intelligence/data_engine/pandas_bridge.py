"""
Bounded Pandas Bridge.
Converts DuckDB query relations to Pandas DataFrames with strict row ceilings and memory safety guards.
"""

from __future__ import annotations

import logging
from typing import Any
import pandas as pd

logger = logging.getLogger("zye.computer_intelligence.bridge")


class BoundedPandasBridge:
    """Safe conversion bridge from DuckDB relations to Pandas DataFrames."""

    @staticmethod
    def materialize_safe(rel: Any, max_rows: int = 100_000) -> pd.DataFrame:
        """Safely materializes a DuckDB relation into a Pandas DataFrame within a row ceiling."""
        try:
            # DuckDB PyRelation limit
            limited_rel = rel.limit(max_rows)
            df = limited_rel.df()
            return df
        except Exception as e:
            logger.error("Pandas bridge materialization failure: %s", e)
            raise RuntimeError(f"Data materialization failed: {e}") from e

    @staticmethod
    def inspect_dataframe_memory(df: pd.DataFrame) -> dict[str, Any]:
        """Calculates precise memory consumption of a DataFrame."""
        mem_bytes = int(df.memory_usage(deep=True).sum())
        return {
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "memory_bytes": mem_bytes,
            "memory_mb": round(mem_bytes / (1024 * 1024), 2),
        }
