"""
Dataset Access Security & File Validation Engine.
Guarantees path safety, format validity, and non-destructive read-only access.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("zye.computer_intelligence.security")

SUPPORTED_EXTENSIONS = {
    ".csv": "CSV",
    ".tsv": "TSV",
    ".gz": "CSV_GZ",
    ".xlsx": "EXCEL_OPENXML",
    ".xls": "EXCEL_LEGACY",
    ".parquet": "PARQUET",
}

# 2GB hard ceiling for local single-file analytics
MAX_DATASET_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB

# Disallowed directory patterns (Windows system boundaries)
PROHIBITED_DIRECTORIES = [
    Path(os.environ.get("SystemRoot", r"C:\Windows")).resolve(),
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")).resolve(),
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")).resolve(),
]


def resolve_dataset_path(file_path: str | Path) -> Path:
    """Resolves and canonicalizes a dataset path."""
    p = Path(file_path).expanduser().resolve()
    return p


def validate_dataset_file(file_path: str | Path) -> dict[str, Any]:
    """Validates that a dataset file exists, has a supported format, is readable,

    and is within authorized directory boundaries.
    """
    if not file_path or not str(file_path).strip():
        return {
            "status": "ERROR",
            "error_code": "DATA_FILE_REQUIRED",
            "message": "A non-empty dataset file path must be provided.",
        }

    try:
        path = resolve_dataset_path(file_path)
    except Exception as e:
        return {
            "status": "ERROR",
            "error_code": "INVALID_PATH_FORMAT",
            "message": f"Failed to resolve path: {e}",
        }

    # 1. Existence check
    if not path.exists():
        return {
            "status": "ERROR",
            "error_code": "DATA_FILE_NOT_FOUND",
            "message": f"Dataset file does not exist: {path}",
        }

    if not path.is_file():
        return {
            "status": "ERROR",
            "error_code": "DATA_NOT_A_FILE",
            "message": f"Path is not a regular file: {path}",
        }

    # 2. System boundary protection
    for prohibited in PROHIBITED_DIRECTORIES:
        try:
            if prohibited in path.parents or path == prohibited:
                return {
                    "status": "ERROR",
                    "error_code": "SECURITY_ACCESS_DENIED",
                    "message": f"Access to system directory is strictly prohibited: {path}",
                }
        except Exception:
            pass

    # 3. Format extension check
    ext = path.suffix.lower()
    # Handle composite .csv.gz
    if ext == ".gz" and path.name.lower().endswith(".csv.gz"):
        format_type = "CSV_GZ"
    elif ext in SUPPORTED_EXTENSIONS:
        format_type = SUPPORTED_EXTENSIONS[ext]
    else:
        return {
            "status": "ERROR",
            "error_code": "UNSUPPORTED_DATA_FORMAT",
            "message": f"File extension '{ext}' is not supported. Supported: {list(SUPPORTED_EXTENSIONS.keys())}",
        }

    # 4. File size check
    try:
        size_bytes = path.stat().st_size
    except Exception as e:
        return {
            "status": "ERROR",
            "error_code": "FILE_STAT_FAILED",
            "message": f"Could not inspect file size: {e}",
        }

    if size_bytes == 0:
        return {
            "status": "ERROR",
            "error_code": "DATA_FILE_CORRUPTED",
            "message": "Dataset file is empty (0 bytes).",
        }

    if size_bytes > MAX_DATASET_FILE_SIZE:
        return {
            "status": "ERROR",
            "error_code": "DATASET_EXCEEDS_SIZE_LIMIT",
            "message": f"Dataset size ({size_bytes / (1024*1024):.1f} MB) exceeds maximum allowed limit ({MAX_DATASET_FILE_SIZE / (1024*1024):.0f} MB).",
        }

    # 5. Read permission check
    if not os.access(str(path), os.R_OK):
        return {
            "status": "ERROR",
            "error_code": "FILE_READ_PERMISSION_DENIED",
            "message": f"Read permission denied for dataset file: {path}",
        }

    return {
        "status": "SUCCESS",
        "path": path,
        "format": format_type,
        "extension": ext,
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
    }
