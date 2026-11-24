"""
Unified Dataset Loader & Backend Dispatcher.
Validates datasets, inspects schemas, and chooses optimal analytical backends.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from zye_computer_intelligence.security.dataset_access import validate_dataset_file
from .schema_inspector import SchemaInspector
from .duckdb_engine import ManagedDuckDB

logger = logging.getLogger("zye.computer_intelligence.loader")


class DatasetLoader:
    """Coordinates validation, metadata extraction, and backend selection."""

    @staticmethod
    def load_and_inspect(file_path: str | Path, sheet_name: str | None = None) -> dict[str, Any]:
        """Validates file and returns complete schema inspection."""
        val = validate_dataset_file(file_path)
        if val["status"] != "SUCCESS":
            return val

        path: Path = val["path"]
        fmt: str = val["format"]

        if fmt in ("CSV", "TSV", "CSV_GZ", "PARQUET"):
            backend = "DUCKDB"
            schema = SchemaInspector.inspect_csv_schema(path)
        elif fmt in ("EXCEL_OPENXML", "EXCEL_LEGACY"):
            backend = "PANDAS"
            schema = SchemaInspector.inspect_excel_schema(path, sheet_name=sheet_name)
        else:
            return {
                "status": "ERROR",
                "error_code": "UNSUPPORTED_DATA_FORMAT",
                "message": f"Unsupported format: {fmt}",
            }

        if schema["status"] != "SUCCESS":
            return schema

        return {
            "status": "SUCCESS",
            "file_path": str(path),
            "file_name": path.name,
            "format": fmt,
            "size_bytes": val["size_bytes"],
            "size_mb": val["size_mb"],
            "backend": backend,
            "schema": schema,
        }
