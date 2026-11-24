"""
Application Execution Schema (Zye Reliability Engineering).
Structured Pydantic models for verified Windows application launching,
eliminating false success and grounding AI responses in empirical window evidence.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ApplicationExecutionStatus(str, Enum):
    """Exhaustive, non-ambiguous status codes for Windows application execution."""
    UI_READY = "UI_READY"
    WINDOW_VISIBLE = "WINDOW_VISIBLE"
    ALREADY_OPEN = "ALREADY_OPEN"
    PROCESS_STARTED = "PROCESS_STARTED"
    WINDOW_TIMEOUT = "WINDOW_TIMEOUT"
    APP_NOT_FOUND = "APP_NOT_FOUND"
    AMBIGUOUS_APP_MATCH = "AMBIGUOUS_APP_MATCH"
    LAUNCH_FAILED = "LAUNCH_FAILED"
    UI_AUTOMATION_UNAVAILABLE = "UI_AUTOMATION_UNAVAILABLE"
    VERIFICATION_INCONCLUSIVE = "VERIFICATION_INCONCLUSIVE"


class ApplicationExecutionResult(BaseModel):
    """
    Standardized, verifiable result schema returned by application launching tools.
    Zero false success: 'verified' is True ONLY when an active window is confirmed on the desktop.
    """
    status: ApplicationExecutionStatus = Field(
        ...,
        description="Empirical execution status. Never reported as UI_READY without window verification.",
    )
    requested_application: str = Field(..., description="Raw application query requested by user")
    resolved_application: str = Field(..., description="Canonical resolved application name")
    appid: Optional[str] = Field(default=None, description="Windows Application User Model ID (AUMID) if available")
    process_id: Optional[int] = Field(default=None, description="Actual observed operating system Process ID")
    window_title: Optional[str] = Field(default=None, description="Actual desktop window title observed")
    hwnd: Optional[int] = Field(default=None, description="Win32 Window Handle (HWND)")
    window_visible: bool = Field(default=False, description="Whether window is verified visible on desktop")
    uia_accessible: bool = Field(default=False, description="Whether window UI Automation tree is accessible")
    launch_method: str = Field(
        default="UNKNOWN",
        description="Method used: DIRECT_EXECUTABLE, APP_PATHS, START_MENU_APPMODEL, or ALREADY_ACTIVE",
    )
    verification_method: str = Field(
        default="NONE",
        description="Verification approach: WINDOW_AND_UIA, WIN32_ENUM_WINDOWS, or PROCESS_ONLY",
    )
    execution_time_ms: float = Field(default=0.0, description="End-to-end launch and verification time in milliseconds")
    verified: bool = Field(
        default=False,
        description="STRICT BOOLEAN: True ONLY if window appeared and is confirmed accessible.",
    )
    message: str = Field(..., description="Human-readable explanation grounded strictly in verified fact")
    candidates: List[str] = Field(default_factory=list, description="Ambiguous application match candidates")
    error: Optional[str] = Field(default=None, description="Specific error details if launch failed")
