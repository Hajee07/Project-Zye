"""
Error Taxonomy for Universal Desktop UI Automation — Zye Day 23.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from zye_office.errors import ZyeOfficeError


class DesktopUIError(ZyeOfficeError):
    def __init__(
        self,
        message: str,
        error_code: str = "UI_AUTOMATION_ERROR",
        remediation: str = "Ensure target application window is open and in the foreground.",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            code=error_code,
            message=message,
            app_name="desktop_ui",
            remediation=remediation,
            details=details,
        )


class UIWindowNotFoundError(DesktopUIError):
    def __init__(self, message: str = "Target desktop application window was not found.") -> None:
        super().__init__(message=message, error_code="UI_WINDOW_NOT_FOUND", remediation="Open the target desktop application.")


class UIForegroundMismatchError(DesktopUIError):
    def __init__(self, expected: str, actual: str) -> None:
        super().__init__(
            message=f"Foreground window mismatch: expected '{expected}', but active window is '{actual}'.",
            error_code="UI_FOREGROUND_WINDOW_MISMATCH",
            remediation="Bring the target window to the foreground before triggering keyboard shortcuts.",
            details={"expected": expected, "actual": actual},
        )


class UIControlNotFoundError(DesktopUIError):
    def __init__(self, control_name: str) -> None:
        super().__init__(
            message=f"UI control '{control_name}' was not found in the active window hierarchy.",
            error_code="UI_CONTROL_NOT_FOUND",
            remediation="Verify accessible control name with desktop_inspect_app_ui().",
            details={"control_name": control_name},
        )


class UIFocusLostError(DesktopUIError):
    def __init__(self, message: str = "Keyboard focus was lost during sequence execution.") -> None:
        super().__init__(message=message, error_code="UI_FOCUS_LOST", remediation="Avoid clicking or switching windows during UI automation.")
