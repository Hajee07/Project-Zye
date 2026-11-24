"""
Duplicate Scan Security Policy.
Enforces authorized directory boundaries, prevents path traversal,
blocks system and credential files, and guarantees strict read-only execution.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Iterable, Tuple

from zye_computer_intelligence.security.local_search_policy import (
    LocalSearchPolicy,
    LocalSearchSecurityError,
    FORBIDDEN_FILE_PATTERNS,
    FORBIDDEN_DIRECTORY_NAMES,
)

logger = logging.getLogger("zye.computer_intelligence.deduplication.security")

SYSTEM_PATH_PREFIXES = {
    "c:\\windows", "c:\\winnt", "c:\\system volume information",
    "c:\\recovery", "/etc", "/var", "/proc", "/sys", "/dev",
}


class DuplicateSecurityError(Exception):
    """Raised when an unauthorized scan directory or destructive operation is requested."""
    pass


class DuplicateScanSecurityPolicy:
    """Zero-trust policy enforcing read-only duplicate detection within authorized scopes."""

    def __init__(
        self,
        allowed_roots: Iterable[str | Path] | None = None,
        max_file_size_bytes: int = 500 * 1024 * 1024, # 500MB
    ) -> None:
        self.search_policy = LocalSearchPolicy(allowed_roots=allowed_roots, max_file_size_bytes=max_file_size_bytes)
        self.max_file_size_bytes = max_file_size_bytes

    @classmethod
    def is_system_directory(cls, path: str | Path) -> bool:
        """Returns True if the path points to or is inside a protected OS or system directory."""
        try:
            p = Path(path).resolve()
            p_str = str(p).lower()

            for prefix in SYSTEM_PATH_PREFIXES:
                if p_str.startswith(prefix.lower()):
                    return True

            for part in p.parts:
                if part.lower() in FORBIDDEN_DIRECTORY_NAMES:
                    return True

            return False
        except Exception:
            return True

    @classmethod
    def validate_scan_directory(cls, dir_path: str | Path) -> Tuple[bool, str]:
        """
        Validates that a directory exists, is a folder, and is not a protected system path.
        Returns:
            (is_valid, reason)
        """
        try:
            target = Path(dir_path).resolve()
        except Exception as e:
            return False, f"Invalid scan path '{dir_path}': {e}"

        if not target.exists():
            return False, f"Scan directory does not exist: {target}"

        if not target.is_dir():
            return False, f"Target is a file, not a directory: {target}"

        if cls.is_system_directory(target):
            return False, f"Access to system or protected directory '{target}' is prohibited"

        return True, "Authorized"

    def is_file_eligible(self, file_path: Path) -> bool:
        """Determines if a file can safely be inspected for duplicate detection."""
        try:
            # Traversal check
            resolved = file_path.resolve()
            if not self.search_policy.is_path_authorized(resolved):
                return False

            # Check filename against forbidden secret patterns
            filename = resolved.name
            for pat in FORBIDDEN_FILE_PATTERNS:
                if pat.match(filename):
                    return False

            # Check directory parts
            for part in resolved.parent.parts:
                if part.lower() in FORBIDDEN_DIRECTORY_NAMES:
                    return False

            # Check file size bound
            stat = resolved.stat()
            if stat.st_size > self.max_file_size_bytes:
                return False

            return True
        except (PermissionError, FileNotFoundError, OSError):
            return False

    @staticmethod
    def enforce_read_only(action_name: str) -> None:
        """Guarantees that no mutation or deletion actions are performed."""
        destructive_verbs = {"delete", "remove", "unlink", "move", "truncate", "overwrite", "rmdir"}
        for verb in destructive_verbs:
            if verb in action_name.lower():
                raise DuplicateSecurityError(
                    f"Action '{action_name}' is forbidden: Duplicate engine is strictly read-only"
                )
