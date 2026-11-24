"""
File Metadata Extraction for Deduplication.
Captures timestamps, byte sizes, file identities, and stability markers.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("zye.computer_intelligence.deduplication.metadata")


def get_file_identity(file_path: Path) -> str:
    """Returns a unique filesystem identity key (device_id:inode) where supported."""
    try:
        stat = file_path.stat()
        # On POSIX and Windows (Python 3.12+), st_dev and st_ino provide file identity
        dev = getattr(stat, "st_dev", 0)
        ino = getattr(stat, "st_ino", 0)
        if ino != 0:
            return f"{dev}:{ino}"
    except Exception:
        pass
    return f"path:{file_path.resolve()}"


def extract_file_metadata(file_path: Path) -> dict[str, Any]:
    """Safely extracts all metadata attributes needed for duplicate identification."""
    try:
        resolved = file_path.resolve()
        stat = resolved.stat()
        return {
            "path": str(resolved),
            "name": resolved.name,
            "extension": resolved.suffix.lower(),
            "size_bytes": stat.st_size,
            "mtime": stat.st_mtime,
            "ctime": stat.st_ctime,
            "file_identity": get_file_identity(resolved),
            "status": "ACCESSIBLE",
        }
    except Exception as exc:
        logger.debug("Failed to extract metadata for '%s': %s", file_path, exc)
        return {
            "path": str(file_path),
            "name": file_path.name,
            "extension": file_path.suffix.lower(),
            "size_bytes": 0,
            "mtime": None,
            "ctime": None,
            "file_identity": None,
            "status": f"UNREADABLE: {exc}",
        }
