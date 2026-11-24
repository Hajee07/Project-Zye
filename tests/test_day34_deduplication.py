"""
Unit Tests for Day 34 SHA-256 Duplicate File Detection Engine.
Verifies streaming 1MB hashing, size grouping, byte-for-byte verification,
hard-link handling, storage calculation, and read-only safety guarantees.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from zye_computer_intelligence.deduplication.duplicate_candidate_filter import group_files_by_size
from zye_computer_intelligence.deduplication.duplicate_classifier import classify_duplicate_group_type
from zye_computer_intelligence.deduplication.duplicate_report_generator import DuplicateReportGenerator
from zye_computer_intelligence.deduplication.duplicate_scan_manager import DuplicateScanManager
from zye_computer_intelligence.deduplication.duplicate_verifier import (
    compare_files_byte_by_byte,
    verify_duplicate_group,
)
from zye_computer_intelligence.deduplication.file_identity import (
    classify_hard_link_copies,
    detect_hard_links,
)
from zye_computer_intelligence.deduplication.file_metadata import extract_file_metadata, get_file_identity
from zye_computer_intelligence.deduplication.sha256_duplicate_engine import SHA256DuplicateEngine
from zye_computer_intelligence.deduplication.storage_calculator import (
    calculate_group_reclaimable_bytes,
    format_bytes_human,
)
from zye_computer_intelligence.deduplication.streaming_hasher import calculate_file_sha256
from zye_computer_intelligence.schemas.duplicate_schemas import (
    DuplicateFileInfo,
    DuplicateGroup,
    DuplicateScanRequest,
    DuplicateType,
    VerificationStatus,
)
from zye_computer_intelligence.security.duplicate_scan_security import (
    DuplicateScanSecurityPolicy,
    DuplicateSecurityError,
)

WORKSPACE_TEST_BASE = Path("d:/Zye/data/test_tmp")


class TestDay34Deduplication(unittest.TestCase):
    """Test suite for SHA-256 duplicate detection engine."""

    def setUp(self):
        WORKSPACE_TEST_BASE.mkdir(parents=True, exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=str(WORKSPACE_TEST_BASE))
        self.dir_path = Path(self.temp_dir.name)

        # Create sample files
        self.content_a = b"ZYE AI Duplicate Detection Test Content Alpha" * 50
        self.content_b = b"ZYE AI Different Content Beta" * 50

        self.file1 = self.dir_path / "file1.txt"
        self.file2 = self.dir_path / "file2.txt"  # Exact duplicate of file1
        self.file3 = self.dir_path / "file3.txt"  # Different content
        self.empty_file = self.dir_path / "empty.txt"

        self.file1.write_bytes(self.content_a)
        self.file2.write_bytes(self.content_a)
        self.file3.write_bytes(self.content_b)
        self.empty_file.write_bytes(b"")

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_streaming_sha256(self):
        """Verifies streaming SHA-256 calculation for non-empty and empty files."""
        sha1, stable1 = calculate_file_sha256(self.file1)
        sha2, stable2 = calculate_file_sha256(self.file2)
        sha3, stable3 = calculate_file_sha256(self.file3)
        sha_empty, stable_empty = calculate_file_sha256(self.empty_file)

        self.assertTrue(stable1)
        self.assertTrue(stable2)
        self.assertTrue(stable3)
        self.assertTrue(stable_empty)

        # Matching files must have identical 64-char hex hashes
        self.assertEqual(len(sha1), 64)
        self.assertEqual(sha1, sha2)
        self.assertNotEqual(sha1, sha3)

        # Empty file standard SHA-256
        self.assertEqual(sha_empty, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    def test_candidate_size_grouping(self):
        """Verifies Stage 1 size filtering: unique sizes are pruned immediately."""
        meta1 = DuplicateFileInfo(**extract_file_metadata(self.file1))
        meta2 = DuplicateFileInfo(**extract_file_metadata(self.file2))
        meta3 = DuplicateFileInfo(**extract_file_metadata(self.file3))

        # file1 and file2 have equal size
        buckets = group_files_by_size([meta1, meta2, meta3])
        self.assertIn(meta1.size_bytes, buckets)
        self.assertEqual(len(buckets[meta1.size_bytes]), 2)

    def test_byte_for_byte_verification(self):
        """Verifies streaming byte comparison between candidates."""
        self.assertTrue(compare_files_byte_by_byte(self.file1, self.file2))
        self.assertFalse(compare_files_byte_by_byte(self.file1, self.file3))

        verified, mismatched = verify_duplicate_group([self.file1, self.file2])
        self.assertTrue(verified)
        self.assertEqual(len(mismatched), 0)

        verified_diff, mismatched_diff = verify_duplicate_group([self.file1, self.file3])
        self.assertFalse(verified_diff)
        self.assertEqual(len(mismatched_diff), 1)

    def test_hard_link_handling_and_storage(self):
        """Verifies hard-link copies detection and reclaimable calculation."""
        f_info_1 = DuplicateFileInfo(
            path=str(self.file1), name="file1.txt", extension=".txt",
            size_bytes=1000, file_identity="1:100", is_hard_link=False
        )
        f_info_2 = DuplicateFileInfo(
            path=str(self.file2), name="file2.txt", extension=".txt",
            size_bytes=1000, file_identity="1:100", is_hard_link=True
        )

        group = DuplicateGroup(
            group_id="grp_test",
            sha256="abc123",
            file_size_bytes=1000,
            file_count=2,
            duplicate_copy_count=1,
            potential_reclaimable_bytes=0,
            files=[f_info_1, f_info_2],
        )

        # Hard-links share physical blocks, so reclaimable must be 0
        reclaimable = calculate_group_reclaimable_bytes(group)
        self.assertEqual(reclaimable, 0)

    def test_storage_calculator_distinct_files(self):
        """Verifies reclaimable calculation for physically distinct duplicates."""
        f1 = DuplicateFileInfo(
            path=str(self.file1), name="f1.txt", extension=".txt",
            size_bytes=2048, file_identity="1:101"
        )
        f2 = DuplicateFileInfo(
            path=str(self.file2), name="f2.txt", extension=".txt",
            size_bytes=2048, file_identity="1:102"
        )

        group = DuplicateGroup(
            group_id="grp_distinct",
            sha256="def456",
            file_size_bytes=2048,
            file_count=2,
            duplicate_copy_count=1,
            potential_reclaimable_bytes=0,
            files=[f1, f2],
        )

        reclaimable = calculate_group_reclaimable_bytes(group)
        self.assertEqual(reclaimable, 2048)
        self.assertEqual(format_bytes_human(2048), "2.00 KB")

    def test_read_only_safety_enforcement(self):
        """Verifies destructive operations raise DuplicateSecurityError."""
        with self.assertRaises(DuplicateSecurityError):
            DuplicateScanSecurityPolicy.enforce_read_only("delete_file")
        with self.assertRaises(DuplicateSecurityError):
            DuplicateScanSecurityPolicy.enforce_read_only("remove_duplicate")

    def test_full_directory_scan_end_to_end(self):
        """Verifies full duplicate detection scan workflow and report generation."""
        res = SHA256DuplicateEngine.scan_directories_sync(
            directories=[str(self.dir_path)],
            recursive=False,
            min_file_size_bytes=1,
        )

        self.assertEqual(res.status, "COMPLETED")
        self.assertGreaterEqual(res.total_files_scanned, 3)
        self.assertEqual(res.duplicate_groups_count, 1)
        self.assertEqual(res.duplicate_files_count, 1)

        # Report formatting
        md_report = SHA256DuplicateEngine.generate_report(res, format="markdown")
        self.assertIn("SHA-256 Duplicate File Audit Report", md_report)
        self.assertIn("READ-ONLY AUDIT", md_report)

        json_report = SHA256DuplicateEngine.generate_report(res, format="json")
        self.assertIn('"scan_id"', json_report)


if __name__ == "__main__":
    unittest.main()
