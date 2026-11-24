"""
Streaming SHA-256 Hasher for File Deduplication.
Calculates cryptographic digests using bounded 1MB chunks to ensure
O(1) memory usage regardless of file size, with pre- and post-read
mutation detection.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger("zye.computer_intelligence.deduplication.hasher")

CHUNK_SIZE = 1024 * 1024  # 1MB chunk buffer


def calculate_file_sha256(file_path: Path, chunk_size: int = CHUNK_SIZE) -> Tuple[str, bool]:
    """
    Computes SHA-256 digest of a file in streaming chunks.
    
    Returns:
        (sha256_hex, is_stable)
        - sha256_hex: 64-character lowercase hexadecimal hash. Empty string if unreadable.
        - is_stable: True if file size and mtime remained unchanged during hashing.
    """
    try:
        resolved = file_path.resolve()
        stat_before = resolved.stat()
        size_before = stat_before.st_size
        mtime_before = stat_before.st_mtime

        hasher = hashlib.sha256()

        if size_before == 0:
            # Empty file - hashlib.sha256() produces e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
            return hasher.hexdigest(), True

        bytes_read = 0
        with open(resolved, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
                bytes_read += len(chunk)

        stat_after = resolved.stat()
        size_after = stat_after.st_size
        mtime_after = stat_after.st_mtime

        is_stable = (size_before == size_after == bytes_read) and (mtime_before == mtime_after)
        if not is_stable:
            logger.warning("File modified during hashing: %s (size: %d -> %d)", file_path, size_before, size_after)

        return hasher.hexdigest(), is_stable

    except Exception as exc:
        logger.warning("Failed to compute SHA-256 for '%s': %s", file_path, exc)
        return "", False
