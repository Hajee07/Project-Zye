"""
Secure File Scanner for Deduplication.
Discovers and inspects files within authorized directory boundaries,
enforcing security bounds, size filters, extension filters, and traversal limits.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Tuple

from zye_computer_intelligence.deduplication.file_metadata import extract_file_metadata
from zye_computer_intelligence.schemas.duplicate_schemas import DuplicateFileInfo, DuplicateScanRequest
from zye_computer_intelligence.security.duplicate_scan_security import DuplicateScanSecurityPolicy
from zye_computer_intelligence.security.processing_resource_policy import ProcessingResourcePolicy

logger = logging.getLogger("zye.computer_intelligence.deduplication.scanner")


class FileScanner:
    """Discovers files within directories respecting security and resource policies."""

    @classmethod
    def scan_directories(cls, request: DuplicateScanRequest) -> Tuple[List[DuplicateFileInfo], List[str]]:
        """
        Scans requested directories and returns:
            (valid_file_infos, unreadable_or_blocked_paths)
        """
        files: List[DuplicateFileInfo] = []
        unreadable: List[str] = []

        # Validate directory access with security policy
        valid_dirs: List[Path] = []
        for d in request.directories:
            p = Path(d)
            is_valid, msg = DuplicateScanSecurityPolicy.validate_scan_directory(p)
            if is_valid:
                valid_dirs.append(p.resolve())
            else:
                logger.warning("Directory '%s' rejected by security policy: %s", d, msg)
                unreadable.append(f"{d} (Rejected: {msg})")

        total_files_collected = 0

        for root_dir in valid_dirs:
            if not root_dir.exists():
                unreadable.append(f"{root_dir} (Directory not found)")
                continue

            try:
                if request.recursive:
                    walker = os.walk(root_dir, topdown=True, followlinks=False)
                else:
                    walker = [(str(root_dir), [], [f.name for f in root_dir.iterdir() if f.is_file()])]

                for dirpath, dirnames, filenames in walker:
                    # Enforce no traversing into system or blacklisted folder names
                    dirnames[:] = [
                        d for d in dirnames
                        if not DuplicateScanSecurityPolicy.is_system_directory(Path(dirpath) / d)
                    ]

                    for filename in filenames:
                        if total_files_collected >= ProcessingResourcePolicy.MAX_TOTAL_FILES_TO_SCAN:
                            logger.info("Reached maximum scan file cap (%d files)", ProcessingResourcePolicy.MAX_TOTAL_FILES_TO_SCAN)
                            return files, unreadable

                        file_path = Path(dirpath) / filename

                        # Extension filtering
                        ext = file_path.suffix.lower()
                        if request.include_extensions and ext not in request.include_extensions:
                            continue
                        if request.exclude_extensions and ext in request.exclude_extensions:
                            continue

                        # Read metadata
                        meta = extract_file_metadata(file_path)
                        if meta["status"] != "ACCESSIBLE":
                            unreadable.append(f"{file_path} ({meta['status']})")
                            continue

                        size = meta["size_bytes"]
                        if size < request.min_file_size_bytes or size > request.max_file_size_bytes:
                            continue

                        files.append(
                            DuplicateFileInfo(
                                path=meta["path"],
                                name=meta["name"],
                                extension=meta["extension"],
                                size_bytes=size,
                                mtime=meta["mtime"],
                                ctime=meta["ctime"],
                                file_identity=meta["file_identity"],
                            )
                        )
                        total_files_collected += 1

            except Exception as exc:
                logger.error("Error walking directory '%s': %s", root_dir, exc)
                unreadable.append(f"{root_dir} (Traversal error: {exc})")

        return files, unreadable
