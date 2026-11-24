"""
Duplicate File Detection Schemas.
Pydantic data models for file discovery, streaming SHA-256 calculation,
byte verification, and storage reclamation analysis.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class DuplicateType(str, Enum):
    EXACT_CONTENT_DUPLICATE = "EXACT_CONTENT_DUPLICATE"
    HARD_LINK_COPIES = "HARD_LINK_COPIES"
    UNSTABLE_MUTATED = "UNSTABLE_MUTATED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    CANDIDATE = "CANDIDATE"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class DuplicateFileInfo(BaseModel):
    path: str = Field(..., description="Absolute normalized path to file")
    name: str = Field(..., description="File name including extension")
    extension: str = Field(..., description="File extension with leading dot")
    size_bytes: int = Field(..., description="File size in bytes")
    mtime: float | None = Field(default=None, description="Modification timestamp")
    ctime: float | None = Field(default=None, description="Creation timestamp")
    file_identity: str | None = Field(default=None, description="Filesystem inode/index identifier")
    is_hard_link: bool = Field(default=False, description="True if identified as hard-link sharing physical storage")


class DuplicateGroup(BaseModel):
    group_id: str = Field(..., description="Unique duplicate group identifier")
    sha256: str = Field(..., description="Full 64-character hex SHA-256 content digest")
    file_size_bytes: int = Field(..., description="Byte size of individual file in this group")
    file_count: int = Field(..., description="Total paths in this duplicate group")
    duplicate_copy_count: int = Field(..., description="Count of duplicate copies (file_count - 1)")
    potential_reclaimable_bytes: int = Field(..., description="Estimated reclaimable storage without double-counting")
    verification_status: VerificationStatus = Field(default=VerificationStatus.VERIFIED)
    duplicate_type: DuplicateType = Field(default=DuplicateType.EXACT_CONTENT_DUPLICATE)
    files: list[DuplicateFileInfo] = Field(default_factory=list)


class DuplicateScanRequest(BaseModel):
    directories: list[str] = Field(..., description="List of authorized directories to scan")
    recursive: bool = Field(default=True, description="Whether to scan child directories recursively")
    min_file_size_bytes: int = Field(default=1, description="Minimum file size to consider (default: 1 byte)")
    max_file_size_bytes: int = Field(default=500 * 1024 * 1024, description="Maximum file size (default: 500MB)")
    include_extensions: list[str] | None = Field(default=None, description="Optional allowlist of file extensions")
    exclude_extensions: list[str] | None = Field(default=None, description="Optional denylist of file extensions")
    verify_bytes: bool = Field(default=True, description="Perform byte-for-byte candidate verification")


class DuplicateScanResult(BaseModel):
    scan_id: str = Field(..., description="Unique scan run identifier")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = Field(default="COMPLETED")
    scan_directories: list[str] = Field(default_factory=list)
    total_files_scanned: int = Field(default=0)
    total_bytes_scanned: int = Field(default=0)
    unique_content_count: int = Field(default=0)
    duplicate_groups_count: int = Field(default=0)
    duplicate_files_count: int = Field(default=0)
    potential_reclaimable_bytes: int = Field(default=0)
    duration_ms: float = Field(default=0.0)
    groups: list[DuplicateGroup] = Field(default_factory=list)
    unreadable_files: list[str] = Field(default_factory=list)
    unstable_files: list[str] = Field(default_factory=list)
    verification_failures: list[str] = Field(default_factory=list)
