"""
Filesystem Identity and Hard Link Resolution.
Detects whether multiple file paths point to identical physical NTFS/POSIX clusters.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple

logger = logging.getLogger("zye.computer_intelligence.deduplication.identity")


def detect_hard_links(file_paths: List[Path]) -> Dict[str, List[Path]]:
    """
    Groups file paths by their filesystem identity (dev:ino).
    Paths sharing the same identity with count > 1 are hard links.
    """
    from zye_computer_intelligence.deduplication.file_metadata import get_file_identity

    identity_map: Dict[str, List[Path]] = {}
    for p in file_paths:
        try:
            ident = get_file_identity(p)
            identity_map.setdefault(ident, []).append(p)
        except Exception:
            identity_map.setdefault(f"path:{p}", []).append(p)

    return identity_map


def classify_hard_link_copies(file_paths: List[Path]) -> Tuple[List[Path], List[Path]]:
    """
    Separates a list of duplicate candidate paths into:
    (unique_physical_paths, hard_link_copies)
    
    unique_physical_paths: distinct inodes/physical files (first one kept).
    hard_link_copies: paths that share an inode with an already seen path.
    """
    from zye_computer_intelligence.deduplication.file_metadata import get_file_identity

    seen_identities: Set[str] = set()
    unique_physical: List[Path] = []
    hard_links: List[Path] = []

    for p in file_paths:
        ident = get_file_identity(p)
        if ident.startswith("path:"):
            unique_physical.append(p)
        elif ident in seen_identities:
            hard_links.append(p)
        else:
            seen_identities.add(ident)
            unique_physical.append(p)

    return unique_physical, hard_links
