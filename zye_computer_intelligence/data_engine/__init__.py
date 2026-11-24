"""
Data Engine Subsystem for Computer Intelligence.
Managed DuckDB execution, query planning, schema inspection, and bounded Pandas integration.
"""

from .duckdb_engine import ManagedDuckDB
from .query_validator import QueryValidator
from .query_planner import QueryPlanner
from .schema_inspector import SchemaInspector
from .dataset_loader import DatasetLoader
from .pandas_bridge import BoundedPandasBridge

__all__ = [
    "ManagedDuckDB",
    "QueryValidator",
    "QueryPlanner",
    "SchemaInspector",
    "DatasetLoader",
    "BoundedPandasBridge",
]
