"""
Streaming Byte-for-Byte Duplicate Verifier.
Performs chunk-by-chunk binary comparison between files with matching SHA-256
digests to provide a zero-collision mathematical guarantee.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger("zye.computer_intelligence.deduplication.verifier")

VERIFY_CHUNK_SIZE = 1024 * 1024  # 1MB comparison buffer


def compare_files_byte_by_byte(path_a: Path, path_b: Path, chunk_size: int = VERIFY_CHUNK_SIZE) -> bool:
    """
    Compares two files byte-by-byte in streaming chunks.
    Returns True if both files are byte-for-byte identical, False otherwise.
    """
    try:
        resolved_a = path_a.resolve()
        resolved_b = path_b.resolve()

        if resolved_a == resolved_b:
            return True

        stat_a = resolved_a.stat()
        stat_b = resolved_b.stat()

        if stat_a.st_size != stat_b.st_size:
            return False

        if stat_a.st_size == 0:
            return True

        with open(resolved_a, "rb") as fa, open(resolved_b, "rb") as fb:
            while True:
                buf_a = fa.read(chunk_size)
                buf_b = fb.read(chunk_size)
                if buf_a != buf_b:
                    return False
                if not buf_a:
                    break

        return True
    except Exception as exc:
        logger.warning("Byte verification error between '%s' and '%s': %s", path_a, path_b, exc)
        return False


def verify_duplicate_group(file_paths: List[Path], chunk_size: int = VERIFY_CHUNK_SIZE) -> Tuple[bool, List[Path]]:
    """
    Verifies all files in a group against the first (reference) file.
    Returns:
        (all_matched, list_of_mismatched_paths)
    """
    if len(file_paths) <= 1:
        return True, []

    reference_path = file_paths[0]
    mismatched: List[Path] = []

    for candidate in file_paths[1:]:
        if not compare_files_byte_by_byte(reference_path, candidate, chunk_size):
            mismatched.append(candidate)

    return (len(mismatched) == 0), mismatched
