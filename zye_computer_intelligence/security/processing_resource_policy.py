"""
Processing Resource Policy.
Defines bounded computational budgets for file scanning, streaming SHA-256 hashing,
and cross-document entity extraction to prevent resource exhaustion.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProcessingResourcePolicy:
    """Resource constraints for file scanning, hashing, and entity parsing."""
    max_files_per_scan: int = 5000
    max_scan_bytes_total: int = 25 * 1024 * 1024 * 1024  # 25 GB total scan budget
    max_single_file_bytes: int = 500 * 1024 * 1024       # 500 MB max single file
    hash_chunk_size_bytes: int = 1024 * 1024             # 1 MB streaming chunk
    max_verification_chunk_bytes: int = 1024 * 1024      # 1 MB candidate byte comparison chunk
    max_documents_per_entity_run: int = 1000             # Max documents to link in a single run
    max_mentions_per_document: int = 500                 # Cap mentions per document
    max_extracted_chars_per_doc: int = 50000             # Text extraction cap
    max_processing_time_seconds: float = 120.0           # Timeout threshold
    max_memory_mb: int = 1024                            # 1 GB soft RAM limit

    # Class-level constants for direct access
    MAX_TOTAL_FILES_TO_SCAN: int = 5000
    MAX_TOTAL_SCAN_BYTES: int = 25 * 1024 * 1024 * 1024
    MAX_DOCUMENTS_PER_ENTITY_RUN: int = 1000
    MAX_SINGLE_FILE_BYTES: int = 500 * 1024 * 1024
