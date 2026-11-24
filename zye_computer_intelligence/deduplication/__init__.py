"""
ZYE AI Deduplication Package.
Cryptographic SHA-256 duplicate detection, hard-link awareness,
byte-for-byte candidate verification, and read-only storage audit.
"""

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
from zye_computer_intelligence.deduplication.file_scanner import FileScanner
from zye_computer_intelligence.deduplication.sha256_duplicate_engine import SHA256DuplicateEngine
from zye_computer_intelligence.deduplication.storage_calculator import (
    calculate_group_reclaimable_bytes,
    format_bytes_human,
)
from zye_computer_intelligence.deduplication.streaming_hasher import calculate_file_sha256

__all__ = [
    "SHA256DuplicateEngine",
    "DuplicateScanManager",
    "FileScanner",
    "calculate_file_sha256",
    "compare_files_byte_by_byte",
    "verify_duplicate_group",
    "extract_file_metadata",
    "get_file_identity",
    "group_files_by_size",
    "detect_hard_links",
    "classify_hard_link_copies",
    "classify_duplicate_group_type",
    "calculate_group_reclaimable_bytes",
    "format_bytes_human",
    "DuplicateReportGenerator",
]
