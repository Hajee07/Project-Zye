"""
Duplicate Classification Engine.
Determines exact classification of candidate groups:
- EXACT_CONTENT_DUPLICATE: Physically separate identical files.
- HARD_LINK_COPIES: Files pointing to the same physical inode on disk.
- UNSTABLE_MUTATED: File changed during hashing.
- VERIFICATION_FAILED: Hash matched but byte comparison failed or file became inaccessible.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple

from zye_computer_intelligence.deduplication.file_identity import classify_hard_link_copies
from zye_computer_intelligence.schemas.duplicate_schemas import (
    DuplicateFileInfo,
    DuplicateType,
    VerificationStatus,
)

logger = logging.getLogger("zye.computer_intelligence.deduplication.classifier")


def classify_duplicate_group_type(
    files: List[DuplicateFileInfo],
    is_verified: bool,
    has_unstable: bool = False,
) -> Tuple[DuplicateType, VerificationStatus]:
    """Classifies duplicate group and sets appropriate verification status."""
    if has_unstable:
        return DuplicateType.UNSTABLE_MUTATED, VerificationStatus.FAILED

    if not is_verified:
        return DuplicateType.VERIFICATION_FAILED, VerificationStatus.FAILED

    # Check if all files in the group are hard links to the same physical file
    file_paths = [Path(f.path) for f in files]
    unique_phys, hard_links = classify_hard_link_copies(file_paths)

    if len(unique_phys) <= 1 and len(hard_links) > 0:
        # All extra paths are hard-links to the single physical file
        return DuplicateType.HARD_LINK_COPIES, VerificationStatus.VERIFIED

    return DuplicateType.EXACT_CONTENT_DUPLICATE, VerificationStatus.VERIFIED
