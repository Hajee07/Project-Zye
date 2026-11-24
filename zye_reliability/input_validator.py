"""
Zye AI — Input Validation Engine (Day 17).
Provides Pydantic-based schemas and functional validation routines for process IDs,
application names, file system paths, audio volume, display brightness, search queries,
and UI interaction parameters.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, Tuple
from pydantic import BaseModel, Field, field_validator


class ValidatedPID(BaseModel):
    pid: int = Field(..., ge=1, le=65535, description="Valid Windows Process ID")


class ValidatedAppName(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Application or process executable name")

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Application name cannot be empty or whitespace.")
        # Check for forbidden control characters or null bytes
        if "\x00" in s or "\n" in s or "\r" in s:
            raise ValueError("Application name contains invalid control characters.")
        return s


class ValidatedPath(BaseModel):
    path: str = Field(..., min_length=1, max_length=1024, description="File system path")

    @field_validator("path")
    @classmethod
    def check_path_security(cls, v: str) -> str:
        if "\x00" in v:
            raise ValueError("Path contains null byte.")
        if v.startswith("\\\\") or v.startswith("//"):
            raise ValueError("UNC and network device paths are not permitted.")
        return v


class ValidatedVolumeLevel(BaseModel):
    level: int = Field(..., ge=0, le=100, description="Volume percentage 0..100")


class ValidatedBrightnessLevel(BaseModel):
    level: int = Field(..., ge=0, le=100, description="Screen brightness percentage 0..100")


class ValidatedSearchQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Search query string")

    @field_validator("query")
    @classmethod
    def clean_query(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Query string cannot be empty or whitespace.")
        if "\x00" in s:
            raise ValueError("Query string contains null byte.")
        return s


class ValidatedScrollAmount(BaseModel):
    amount: int = Field(..., ge=1, le=50, description="Scroll click count 1..50")


def validate_pid(pid: Any) -> Tuple[bool, Any]:
    """Validate process ID integer."""
    try:
        val = int(pid)
        model = ValidatedPID(pid=val)
        return True, model.pid
    except Exception as exc:
        return False, f"Invalid PID: {exc}"


def validate_app_name(name: Any) -> Tuple[bool, Any]:
    """Validate application name string."""
    try:
        if not isinstance(name, str):
            return False, "Application name must be a string."
        model = ValidatedAppName(name=name)
        return True, model.name
    except Exception as exc:
        return False, f"Invalid application name: {exc}"


def validate_path(path: Any, project_root: Optional[Path] = None) -> Tuple[bool, Any]:
    """Validate path string and optionally check project root containment."""
    try:
        if not isinstance(path, (str, Path)):
            return False, "Path must be a string or Path object."
        s = str(path).strip()
        model = ValidatedPath(path=s)
        p = Path(model.path)

        if project_root is not None:
            root_res = project_root.resolve()
            target_res = (root_res / p).resolve() if not p.is_absolute() else p.resolve()
            try:
                target_res.relative_to(root_res)
            except ValueError:
                return False, f"Path escapes project boundary: {target_res}"
            return True, target_res

        return True, p
    except Exception as exc:
        return False, f"Invalid path: {exc}"


def validate_volume(level: Any) -> Tuple[bool, Any]:
    """Validate volume level percentage (0..100)."""
    try:
        val = int(level)
        model = ValidatedVolumeLevel(level=val)
        return True, model.level
    except Exception as exc:
        return False, f"Invalid volume level: {exc}"


def validate_brightness(level: Any) -> Tuple[bool, Any]:
    """Validate screen brightness percentage (0..100)."""
    try:
        val = int(level)
        model = ValidatedBrightnessLevel(level=val)
        return True, model.level
    except Exception as exc:
        return False, f"Invalid brightness level: {exc}"


def validate_search_query(query: Any) -> Tuple[bool, Any]:
    """Validate search query string."""
    try:
        if not isinstance(query, str):
            return False, "Query must be a string."
        model = ValidatedSearchQuery(query=query)
        return True, model.query
    except Exception as exc:
        return False, f"Invalid search query: {exc}"


def validate_scroll_amount(amount: Any) -> Tuple[bool, Any]:
    """Validate scroll click amount (1..50)."""
    try:
        val = int(amount)
        model = ValidatedScrollAmount(amount=val)
        return True, model.amount
    except Exception as exc:
        return False, f"Invalid scroll amount: {exc}"
