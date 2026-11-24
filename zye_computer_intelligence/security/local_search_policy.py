"""
Local Search Security Policy & Path Validation.
Enforces strict directory boundary enforcement, prevents path traversal,
and shields sensitive credentials, keys, certificates, and system folders.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Iterable

logger = logging.getLogger("zye.computer_intelligence.search_security")

DEFAULT_MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25MB

# Forbidden sensitive patterns
FORBIDDEN_FILE_PATTERNS = [
    re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
    re.compile(r".*id_rsa.*", re.IGNORECASE),
    re.compile(r".*\.pem$", re.IGNORECASE),
    re.compile(r".*\.key$", re.IGNORECASE),
    re.compile(r".*\.pfx$", re.IGNORECASE),
    re.compile(r".*\.kdbx$", re.IGNORECASE),
    re.compile(r".*credential.*", re.IGNORECASE),
    re.compile(r".*password.*\.txt$", re.IGNORECASE),
    re.compile(r"^cookies.*", re.IGNORECASE),
    re.compile(r"^login data.*", re.IGNORECASE),
    re.compile(r"^web data.*", re.IGNORECASE),
]

FORBIDDEN_DIRECTORY_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "appdata",
    "windows",
    "system32",
    "program files",
    "program files (x86)",
}

ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".pdf", ".docx", ".xlsx", ".xls", ".csv",
    ".json", ".py", ".js", ".ts", ".html", ".htm", ".xml",
    ".yaml", ".yml", ".toml", ".sql", ".db", ".duckdb", ".sqlite",
}


class LocalSearchSecurityError(Exception):
    """Raised when an unauthorized path or sensitive file access is attempted."""
    pass


class LocalSearchPolicy:
    """Validates local search boundaries, file paths, extensions, and sizes."""

    def __init__(
        self,
        allowed_roots: Iterable[str | Path] | None = None,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
    ) -> None:
        self.max_file_size = max_file_size_bytes
        if allowed_roots:
            self.allowed_roots = [Path(r).resolve() for r in allowed_roots]
        else:
            # Default to current workspace / project root
            workspace = Path(os.environ.get("ZYE_WORKSPACE", "d:/Zye")).resolve()
            self.allowed_roots = [workspace]

    def add_allowed_root(self, root_path: str | Path) -> None:
        """Adds an authorized directory root to search scope."""
        p = Path(root_path).resolve()
        if p.exists() and p.is_dir():
            if p not in self.allowed_roots:
                self.allowed_roots.append(p)
        else:
            raise LocalSearchSecurityError(f"Cannot authorize non-existent directory: {root_path}")

    def is_path_authorized(self, file_path: str | Path) -> bool:
        """Checks whether file_path falls within an authorized root directory."""
        try:
            target = Path(file_path).resolve()
            for root in self.allowed_roots:
                try:
                    target.relative_to(root)
                    return True
                except ValueError:
                    continue
            return False
        except Exception:
            return False

    def is_directory_allowed(self, dir_path: str | Path) -> bool:
        """Returns True if directory is allowed (not restricted, not hidden)."""
        try:
            target = Path(dir_path).resolve()
            for part in target.parts:
                low = part.lower()
                if low in FORBIDDEN_DIRECTORY_NAMES or (part.startswith(".") and part not in (".", "..")):
                    return False
            return True
        except Exception:
            return False

    def validate_file_access(self, file_path: str | Path) -> Path:
        """Validates path boundary, traversal defense, extension whitelist, and sensitive content filters."""
        target = Path(file_path).resolve()

        if not self.is_path_authorized(target):
            raise LocalSearchSecurityError(
                f"Access denied: '{target}' is outside authorized search roots."
            )

        # Check directory parts for forbidden system / internal dirs
        for part in target.parts:
            if part.lower() in FORBIDDEN_DIRECTORY_NAMES:
                raise LocalSearchSecurityError(
                    f"Access denied: Searching inside restricted folder '{part}' is prohibited."
                )

        # Check filename against sensitive patterns
        filename = target.name
        for pattern in FORBIDDEN_FILE_PATTERNS:
            if pattern.match(filename):
                raise LocalSearchSecurityError(
                    f"Access denied: Sensitive file '{filename}' cannot be searched or indexed."
                )

        # Check extension whitelist
        if target.is_file():
            if target.suffix.lower() not in ALLOWED_EXTENSIONS:
                raise LocalSearchSecurityError(
                    f"Unsupported extension '{target.suffix}'. Allowed: {sorted(list(ALLOWED_EXTENSIONS))}"
                )

            # Check file size
            try:
                size = target.stat().st_size
                if size > self.max_file_size:
                    raise LocalSearchSecurityError(
                        f"File size {size} bytes exceeds maximum allowed {self.max_file_size} bytes."
                    )
            except OSError as e:
                raise LocalSearchSecurityError(f"Could not stat file: {e}")

        return target

    @classmethod
    def validate_search_path(cls, file_path: str | Path) -> tuple[bool, str]:
        """Validates file access against default workspace search policy."""
        try:
            policy = cls()
            policy.validate_file_access(file_path)
            return True, "Authorized"
        except Exception as e:
            return False, str(e)
