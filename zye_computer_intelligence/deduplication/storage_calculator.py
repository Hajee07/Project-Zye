"""
Storage Reclamation Calculator.
Accurately estimates duplicate bytes and potential storage savings
without double counting hard links or identical inodes.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Set

from zye_computer_intelligence.deduplication.file_identity import classify_hard_link_copies
from zye_computer_intelligence.schemas.duplicate_schemas import DuplicateFileInfo, DuplicateGroup

logger = logging.getLogger("zye.computer_intelligence.deduplication.storage_calculator")


def calculate_group_reclaimable_bytes(group: DuplicateGroup) -> int:
    """
    Computes reclaimable bytes for a duplicate group.
    - If hard links share an inode, they do not occupy extra physical disk space.
    - For M physical copies of size S, keeping 1 copy leaves (M - 1) * S reclaimable.
    """
    if len(group.files) <= 1:
        return 0

    seen_identities: Set[str] = set()
    physical_count = 0

    for f in group.files:
        if f.is_hard_link:
            continue
        ident = f.file_identity
        if ident and not ident.startswith("path:"):
            if ident in seen_identities:
                continue
            seen_identities.add(ident)
            physical_count += 1
        else:
            physical_count += 1

    if physical_count > 1:
        return (physical_count - 1) * group.file_size_bytes
    return 0


def format_bytes_human(num_bytes: int) -> str:
    """Formats raw bytes into human readable string (e.g. 14.50 MB)."""
    val = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(val) < 1024.0:
            return f"{val:.2f} {unit}"
        val /= 1024.0
    return f"{val:.2f} PB"
