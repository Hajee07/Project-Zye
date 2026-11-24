"""
Office Path & Document Security Validator — Zye Day 20.
Enforces workspace boundaries, path traversal prevention, valid Office/PDF extensions,
and confirmation gates for file overwriting.
"""

from __future__ import annotations

import logging
import os
import pathlib
from typing import Any, Optional

logger = logging.getLogger("zye.office.path_validator")

# Allowed Office & Export file extensions
ALLOWED_OFFICE_EXTENSIONS = frozenset({
    ".docx", ".doc", ".dotx", ".docm",
    ".xlsx", ".xls", ".xltx", ".xlsm", ".csv",
    ".pptx", ".ppt", ".potx", ".pptm",
    ".pdf",
})

DEFAULT_WORKSPACE_ROOT = pathlib.Path(__file__).resolve().parent.parent


class OfficePathValidator:
    """
    Validates input and output file paths against traversal, workspace limits,
    and irreversible overwriting.
    """

    def __init__(self, workspace_root: Optional[pathlib.Path] = None) -> None:
        self.workspace_root = (workspace_root or DEFAULT_WORKSPACE_ROOT).resolve()

    def validate_path(
        self,
        path_str: str,
        app_type: Optional[Any] = None,
        allowed_extensions: Optional[Any] = None,
        must_exist: bool = False,
    ) -> str:
        """Validate path string and return canonical string or raise appropriate exception."""
        from zye_office.errors import OfficeSecurityError, OfficeValidationError
        exts = frozenset(allowed_extensions) if allowed_extensions else None
        res = self.validate_file_path(path_str, must_exist=must_exist, allowed_extensions=exts)
        if res.get("status") == "REJECTED":
            if res.get("error_code") == "OFFICE_PATH_TRAVERSAL_DETECTED":
                raise OfficeSecurityError(res.get("message", "Path traversal detected"))
            raise OfficeValidationError(res.get("message", "Invalid path"))
        elif res.get("status") not in ("SUCCESS", "VALID"):
            raise OfficeValidationError(res.get("message", "Path validation failed"))
        return str(res.get("canonical_path") or res.get("path_str"))

    def validate_file_path(
        self,
        path_str: str,
        must_exist: bool = False,
        allowed_extensions: Optional[frozenset[str]] = None,
        require_inside_workspace: bool = False,
    ) -> dict[str, Any]:
        """
        Validate a file path string. Resolves absolute canonical path,
        checks traversal, verifies extension, and ensures parent directory exists.
        """
        if not path_str or not str(path_str).strip():
            return {
                "status": "ERROR",
                "error_code": "OFFICE_INVALID_PATH",
                "message": "File path cannot be empty.",
            }

        clean = str(path_str).strip()
        # Traversal character check in raw string
        if ".." in clean:
            return {
                "status": "REJECTED",
                "error_code": "OFFICE_PATH_TRAVERSAL_DETECTED",
                "message": "Path traversal ('..') is not permitted.",
                "path": clean,
            }

        try:
            target = pathlib.Path(clean)
            if not target.is_absolute():
                target = (self.workspace_root / target).resolve()
            else:
                target = target.resolve()
        except Exception as exc:
            return {
                "status": "ERROR",
                "error_code": "OFFICE_INVALID_PATH",
                "message": f"Malformed file path: {exc}",
                "path": clean,
            }

        # Boundary check if required
        if require_inside_workspace:
            try:
                target.relative_to(self.workspace_root)
            except ValueError:
                return {
                    "status": "REJECTED",
                    "error_code": "OFFICE_PATH_OUTSIDE_WORKSPACE",
                    "message": f"Path '{target}' is outside the authorized workspace directory '{self.workspace_root}'.",
                    "path": str(target),
                }

        # Extension check
        exts = allowed_extensions or ALLOWED_OFFICE_EXTENSIONS
        if target.suffix.lower() not in exts:
            return {
                "status": "REJECTED",
                "error_code": "OFFICE_UNAUTHORIZED_EXTENSION",
                "message": f"Extension '{target.suffix}' is not authorized. Allowed: {sorted(list(exts))}",
                "path": str(target),
            }

        # Existence check
        if must_exist and not target.is_file():
            return {
                "status": "NOT_FOUND",
                "error_code": "OFFICE_FILE_NOT_FOUND",
                "message": f"File does not exist: {target}",
                "path": str(target),
            }

        # Ensure parent directory exists or can be created
        if not target.parent.exists():
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                return {
                    "status": "ERROR",
                    "error_code": "OFFICE_PARENT_DIR_CREATE_FAILED",
                    "message": f"Could not create parent directory '{target.parent}': {exc}",
                }

        return {
            "status": "VALID",
            "path": target,
            "path_str": str(target),
            "filename": target.name,
            "extension": target.suffix.lower(),
            "exists": target.exists(),
        }

    def validate_overwrite(
        self,
        target_path: pathlib.Path,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """
        Check if destination file already exists and enforce confirmation gate before overwrite.
        """
        if target_path.exists():
            if not confirmed:
                return {
                    "status": "CONFIRMATION_REQUIRED",
                    "error_code": "OFFICE_CONFIRMATION_REQUIRED",
                    "message": f"Destination file '{target_path.name}' already exists. Overwrite will erase existing content. Call with confirmed=True to proceed.",
                    "requires_confirmation": True,
                    "target_path": str(target_path),
                }

        return {
            "status": "ALLOWED",
            "target_path": str(target_path),
        }
