"""
Duplicate Scan Manager.
Orchestrates multi-stage deduplication pipeline:
1. File discovery & metadata filtering
2. Size bucket partitioning (instant pruning of unique sizes)
3. 1MB streaming SHA-256 calculation
4. 1MB streaming byte-for-byte candidate verification
5. Hard link detection and physical storage calculation
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from zye_computer_intelligence.deduplication.duplicate_candidate_filter import group_files_by_size
from zye_computer_intelligence.deduplication.duplicate_classifier import classify_duplicate_group_type
from zye_computer_intelligence.deduplication.duplicate_verifier import verify_duplicate_group
from zye_computer_intelligence.deduplication.file_identity import classify_hard_link_copies
from zye_computer_intelligence.deduplication.file_scanner import FileScanner
from zye_computer_intelligence.deduplication.storage_calculator import calculate_group_reclaimable_bytes
from zye_computer_intelligence.deduplication.streaming_hasher import calculate_file_sha256
from zye_computer_intelligence.schemas.duplicate_schemas import (
    DuplicateFileInfo,
    DuplicateGroup,
    DuplicateScanRequest,
    DuplicateScanResult,
    VerificationStatus,
)

logger = logging.getLogger("zye.computer_intelligence.deduplication.manager")


class DuplicateScanManager:
    """Orchestrates end-to-end safe duplicate scanning."""

    @classmethod
    def execute_scan(cls, request: DuplicateScanRequest) -> DuplicateScanResult:
        """Executes full duplicate detection workflow."""
        start_time = time.perf_counter()
        scan_id = f"dup_{uuid.uuid4().hex[:12]}"

        # Step 1: Discover files
        discovered_files, unreadable = FileScanner.scan_directories(request)
        total_files = len(discovered_files)
        total_bytes = sum(f.size_bytes for f in discovered_files)

        # Step 2: Size bucket partitioning
        size_buckets = group_files_by_size(discovered_files)

        unstable_files: List[str] = []
        verification_failures: List[str] = []
        duplicate_groups: List[DuplicateGroup] = []

        total_reclaimable = 0
        total_duplicate_copies = 0
        unique_contents = set()

        # Step 3: Stream hash files that share sizes
        for size, file_list in size_buckets.items():
            # Group by sha256 within size bucket
            hash_buckets: Dict[str, List[DuplicateFileInfo]] = defaultdict(list)

            for f_info in file_list:
                f_path = Path(f_info.path)
                sha, is_stable = calculate_file_sha256(f_path)

                if not is_stable:
                    unstable_files.append(f_info.path)
                    continue

                if not sha:
                    unreadable.append(f_info.path)
                    continue

                hash_buckets[sha].append(f_info)

            # Step 4: Verify and classify matching hashes
            for sha, matched_files in hash_buckets.items():
                unique_contents.add(sha)
                if len(matched_files) <= 1:
                    continue  # Only 1 file with this hash

                matched_paths = [Path(f.path) for f in matched_files]
                is_verified = True

                if request.verify_bytes:
                    verified, mismatched = verify_duplicate_group(matched_paths)
                    if not verified:
                        is_verified = False
                        for m in mismatched:
                            verification_failures.append(str(m))

                # Step 5: Hard link detection
                _, hard_links = classify_hard_link_copies(matched_paths)
                hard_link_set = {str(hl.resolve()) for hl in hard_links}

                for f_info in matched_files:
                    try:
                        resolved_str = str(Path(f_info.path).resolve())
                        if resolved_str in hard_link_set:
                            f_info.is_hard_link = True
                    except Exception:
                        pass

                dup_type, ver_status = classify_duplicate_group_type(
                    files=matched_files,
                    is_verified=is_verified,
                    has_unstable=False,
                )

                group_id = f"grp_{uuid.uuid4().hex[:8]}"
                duplicate_count = len(matched_files) - 1
                total_duplicate_copies += duplicate_count

                temp_group = DuplicateGroup(
                    group_id=group_id,
                    sha256=sha,
                    file_size_bytes=size,
                    file_count=len(matched_files),
                    duplicate_copy_count=duplicate_count,
                    potential_reclaimable_bytes=0,
                    verification_status=ver_status,
                    duplicate_type=dup_type,
                    files=matched_files,
                )

                reclaimable = calculate_group_reclaimable_bytes(temp_group)
                temp_group.potential_reclaimable_bytes = reclaimable
                total_reclaimable += reclaimable

                duplicate_groups.append(temp_group)

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        return DuplicateScanResult(
            scan_id=scan_id,
            status="COMPLETED",
            scan_directories=request.directories,
            total_files_scanned=total_files,
            total_bytes_scanned=total_bytes,
            unique_content_count=len(unique_contents),
            duplicate_groups_count=len(duplicate_groups),
            duplicate_files_count=total_duplicate_copies,
            potential_reclaimable_bytes=total_reclaimable,
            duration_ms=duration_ms,
            groups=duplicate_groups,
            unreadable_files=unreadable,
            unstable_files=unstable_files,
            verification_failures=verification_failures,
        )
