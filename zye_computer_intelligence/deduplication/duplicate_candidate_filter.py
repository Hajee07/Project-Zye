"""
Multi-Stage Candidate Filtering for File Deduplication.
Stage 1: Groups files by byte size. Files with unique sizes are pruned
instantly without invoking cryptographic hash operations.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from zye_computer_intelligence.schemas.duplicate_schemas import DuplicateFileInfo

logger = logging.getLogger("zye.computer_intelligence.deduplication.candidate_filter")


def group_files_by_size(files: List[DuplicateFileInfo]) -> Dict[int, List[DuplicateFileInfo]]:
    """
    Groups file metadata by size_bytes.
    Only returns groups that have 2 or more files (potential duplicate candidates).
    """
    size_buckets: Dict[int, List[DuplicateFileInfo]] = defaultdict(list)
    for info in files:
        if info.size_bytes >= 0:
            size_buckets[info.size_bytes].append(info)

    candidate_buckets = {
        size: file_list for size, file_list in size_buckets.items() if len(file_list) > 1
    }

    logger.debug(
        "Candidate filtering: %d total files -> %d size buckets with potential duplicates",
        len(files),
        len(candidate_buckets),
    )
    return candidate_buckets
