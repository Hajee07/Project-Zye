"""
SHA-256 Duplicate File Detection Engine Facade.
Main entry point for scanning directories, comparing files, and generating reports.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from zye_computer_intelligence.deduplication.duplicate_report_generator import DuplicateReportGenerator
from zye_computer_intelligence.deduplication.duplicate_scan_manager import DuplicateScanManager
from zye_computer_intelligence.deduplication.duplicate_verifier import compare_files_byte_by_byte
from zye_computer_intelligence.deduplication.streaming_hasher import calculate_file_sha256
from zye_computer_intelligence.schemas.duplicate_schemas import (
    DuplicateScanRequest,
    DuplicateScanResult,
)

logger = logging.getLogger("zye.computer_intelligence.deduplication.engine")


class SHA256DuplicateEngine:
    """High-level interface for cryptographic file deduplication."""

    @classmethod
    def scan_directories_sync(
        cls,
        directories: List[str],
        recursive: bool = True,
        min_file_size_bytes: int = 1,
        max_file_size_bytes: int = 500 * 1024 * 1024,
        include_extensions: Optional[List[str]] = None,
        exclude_extensions: Optional[List[str]] = None,
        verify_bytes: bool = True,
    ) -> DuplicateScanResult:
        """Runs deduplication scan synchronously."""
        request = DuplicateScanRequest(
            directories=directories,
            recursive=recursive,
            min_file_size_bytes=min_file_size_bytes,
            max_file_size_bytes=max_file_size_bytes,
            include_extensions=include_extensions,
            exclude_extensions=exclude_extensions,
            verify_bytes=verify_bytes,
        )
        return DuplicateScanManager.execute_scan(request)

    @classmethod
    async def scan_directories(
        cls,
        directories: List[str],
        recursive: bool = True,
        min_file_size_bytes: int = 1,
        max_file_size_bytes: int = 500 * 1024 * 1024,
        include_extensions: Optional[List[str]] = None,
        exclude_extensions: Optional[List[str]] = None,
        verify_bytes: bool = True,
    ) -> DuplicateScanResult:
        """Runs deduplication scan asynchronously in a threadpool worker."""
        return await asyncio.to_thread(
            cls.scan_directories_sync,
            directories=directories,
            recursive=recursive,
            min_file_size_bytes=min_file_size_bytes,
            max_file_size_bytes=max_file_size_bytes,
            include_extensions=include_extensions,
            exclude_extensions=exclude_extensions,
            verify_bytes=verify_bytes,
        )

    @classmethod
    def compare_two_files(cls, path_a: str, path_b: str, verify_bytes: bool = True) -> Dict[str, Any]:
        """Compares two specific files for exact duplicates."""
        pa = Path(path_a)
        pb = Path(path_b)

        if not pa.exists() or not pb.exists():
            return {
                "match": False,
                "error": "One or both files do not exist",
                "path_a": str(pa),
                "path_b": str(pb),
            }

        size_a = pa.stat().st_size
        size_b = pb.stat().st_size
        if size_a != size_b:
            return {
                "match": False,
                "reason": "File sizes differ",
                "size_a": size_a,
                "size_b": size_b,
            }

        sha_a, stable_a = calculate_file_sha256(pa)
        sha_b, stable_b = calculate_file_sha256(pb)

        if not stable_a or not stable_b:
            return {
                "match": False,
                "reason": "One or both files were modified during reading",
            }

        hashes_match = (sha_a == sha_b) and bool(sha_a)
        bytes_match = True
        if hashes_match and verify_bytes:
            bytes_match = compare_files_byte_by_byte(pa, pb)

        return {
            "match": hashes_match and bytes_match,
            "sha256_match": hashes_match,
            "bytes_match": bytes_match,
            "sha256": sha_a,
            "size_bytes": size_a,
            "path_a": str(pa.resolve()),
            "path_b": str(pb.resolve()),
        }

    @classmethod
    def generate_report(cls, result: DuplicateScanResult, format: str = "markdown") -> str:
        """Formats scan result into Markdown or JSON report."""
        if format.lower() == "json":
            return DuplicateReportGenerator.generate_json_report(result)
        return DuplicateReportGenerator.generate_markdown_report(result)
