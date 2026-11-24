"""
Structured Error Taxonomy for Microsoft PowerPoint Automation — Zye Day 23.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from zye_office.errors import ZyeOfficeError


class PowerPointAutomationError(ZyeOfficeError):
    def __init__(
        self,
        message: str,
        error_code: str = "POWERPOINT_AUTOMATION_ERROR",
        remediation: str = "Ensure Microsoft PowerPoint is installed and running.",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            code=error_code,
            message=message,
            app_name="powerpoint",
            remediation=remediation,
            details=details,
        )


class PowerPointNotInstalledError(PowerPointAutomationError):
    def __init__(self, message: str = "Microsoft PowerPoint is not installed or registered.") -> None:
        super().__init__(message=message, error_code="POWERPOINT_NOT_INSTALLED", remediation="Install Microsoft Office.")


class PowerPointCOMUnavailableError(PowerPointAutomationError):
    def __init__(self, message: str = "PowerPoint COM application interface is unreachable.") -> None:
        super().__init__(message=message, error_code="POWERPOINT_COM_UNAVAILABLE", remediation="Restart PowerPoint.")


class PowerPointNoActivePresentationError(PowerPointAutomationError):
    def __init__(self, message: str = "PowerPoint is running, but no presentation is open.") -> None:
        super().__init__(message=message, error_code="POWERPOINT_NO_ACTIVE_PRESENTATION", remediation="Open or create a presentation.")


class PowerPointSlideNotFoundError(PowerPointAutomationError):
    def __init__(self, slide_index: int) -> None:
        super().__init__(
            message=f"Slide index {slide_index} was not found in the active presentation.",
            error_code="POWERPOINT_SLIDE_NOT_FOUND",
            remediation="Verify the slide count using powerpoint_get_slides().",
            details={"slide_index": slide_index},
        )


class PowerPointTransitionError(PowerPointAutomationError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, error_code="POWERPOINT_TRANSITION_UNSUPPORTED", remediation="Select a standard transition like Fade, Push, or Wipe.")


class PowerPointAnimationError(PowerPointAutomationError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, error_code="POWERPOINT_ANIMATION_UNSUPPORTED", remediation="Ensure target shape exists on slide and effect is valid.")


class PowerPointShapeNotFoundError(PowerPointAutomationError):
    def __init__(self, shape_name: str) -> None:
        super().__init__(
            message=f"Shape '{shape_name}' was not found on the specified slide.",
            error_code="POWERPOINT_SHAPE_NOT_FOUND",
            remediation="Inspect slide shapes with powerpoint_get_slide_metadata().",
            details={"shape": shape_name},
        )
