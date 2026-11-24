"""
Structured Error Taxonomy — Zye Day 20 Microsoft Office COM Automation.
Unified exception classes and structured error response formatters.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional, Union


class ZyeOfficeError(Exception):
    """Base exception for all Microsoft Office automation errors."""

    def __init__(
        self,
        code: str,
        message: str,
        app_name: str = "office",
        operation_id: Optional[str] = None,
        retryable: bool = False,
        remediation: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.app_name = app_name
        self.operation_id = operation_id
        self.retryable = retryable
        self.remediation = remediation
        self.details = details or {}
        self.trace_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to clean, JSON-serializable structured error dict."""
        res: dict[str, Any] = {
            "status": "ERROR",
            "error_code": self.code,
            "message": self.message,
            "app_name": self.app_name,
            "trace_id": self.trace_id,
            "retryable": self.retryable,
        }
        if self.operation_id:
            res["operation_id"] = self.operation_id
        if self.remediation:
            res["remediation"] = self.remediation
        if self.details:
            res["details"] = self.details
        return res


# Aliases & Subclasses for clean semantic handling
OfficeAutomationError = ZyeOfficeError


class COMInitializationError(ZyeOfficeError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__("COM_INITIALIZATION_FAILED", message, **kwargs)


class COMAppUnavailableError(ZyeOfficeError):
    def __init__(self, app_name: str, message: str, **kwargs: Any) -> None:
        super().__init__("COM_APPLICATION_UNAVAILABLE", message, app_name=app_name, **kwargs)


class COMDisconnectedError(ZyeOfficeError):
    def __init__(self, app_name: str, message: str, **kwargs: Any) -> None:
        super().__init__("COM_DISCONNECTED", message, app_name=app_name, retryable=True, **kwargs)


class OfficeCOMError(ZyeOfficeError):
    def __init__(self, message: str, code: str = "COM_OPERATION_ERROR", app_name: str = "office", **kwargs: Any) -> None:
        super().__init__(code, message, app_name=app_name, **kwargs)


class OfficeConnectionError(ZyeOfficeError):
    def __init__(self, message: str, code: str = "CONNECTION_ERROR", app_name: str = "office", **kwargs: Any) -> None:
        super().__init__(code, message, app_name=app_name, **kwargs)


class OfficeSessionError(ZyeOfficeError):
    def __init__(self, message: str, code: str = "SESSION_ERROR", app_name: str = "office", **kwargs: Any) -> None:
        super().__init__(code, message, app_name=app_name, **kwargs)


class OfficeOperationError(ZyeOfficeError):
    def __init__(self, message: str, code: str = "OPERATION_ERROR", app_name: str = "office", **kwargs: Any) -> None:
        super().__init__(code, message, app_name=app_name, **kwargs)


class OfficeValidationError(ZyeOfficeError):
    def __init__(self, message: str, code: str = "VALIDATION_ERROR", app_name: str = "office", **kwargs: Any) -> None:
        super().__init__(code, message, app_name=app_name, **kwargs)


class OfficeInspectionError(ZyeOfficeError):
    def __init__(self, message: str, code: str = "INSPECTION_ERROR", app_name: str = "office", **kwargs: Any) -> None:
        super().__init__(code, message, app_name=app_name, **kwargs)


class OfficeFileExportError(ZyeOfficeError):
    def __init__(self, message: str, code: str = "EXPORT_ERROR", app_name: str = "office", **kwargs: Any) -> None:
        super().__init__(code, message, app_name=app_name, **kwargs)


# Application Specific Errors
class WordAutomationError(ZyeOfficeError):
    def __init__(self, code: str = "WORD_ERROR", message: str = "", **kwargs: Any) -> None:
        super().__init__(code, message, app_name="word", **kwargs)


class ExcelAutomationError(ZyeOfficeError):
    def __init__(self, code: str = "EXCEL_ERROR", message: str = "", **kwargs: Any) -> None:
        super().__init__(code, message, app_name="excel", **kwargs)


class PowerPointAutomationError(ZyeOfficeError):
    def __init__(self, code: str = "POWERPOINT_ERROR", message: str = "", **kwargs: Any) -> None:
        super().__init__(code, message, app_name="powerpoint", **kwargs)


class OutlookAutomationError(ZyeOfficeError):
    def __init__(self, code: str = "OUTLOOK_ERROR", message: str = "", **kwargs: Any) -> None:
        super().__init__(code, message, app_name="outlook", **kwargs)


# Export & Security Errors
class PDFExportError(OfficeFileExportError):
    def __init__(self, message: str, code: str = "PDF_EXPORT_ERROR", app_name: str = "office", **kwargs: Any) -> None:
        super().__init__(message, code=code, app_name=app_name, **kwargs)


class OfficeSecurityError(ZyeOfficeError):
    def __init__(self, message: str, code: str = "SECURITY_VIOLATION", app_name: str = "office", **kwargs: Any) -> None:
        super().__init__(code, message, app_name=app_name, **kwargs)


def format_office_error(
    error_or_code: Union[Exception, str] = "OFFICE_ERROR",
    message: Optional[str] = None,
    app_name: str = "office",
    operation_id: Optional[str] = None,
    retryable: bool = False,
    remediation: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    context: Optional[str] = None,
    error_code: Optional[str] = None,
) -> dict[str, Any]:
    """
    Flexible helper to generate structured error dictionary from an Exception
    or from an explicit error code + message.
    """
    if error_code:
        code = error_code
        msg = message or ""
        err = ZyeOfficeError(
            code=code,
            message=msg,
            app_name=app_name,
            operation_id=operation_id,
            retryable=retryable,
            remediation=remediation,
            details=details or ({"context": context} if context else None),
        )
        return err.to_dict()

    if isinstance(error_or_code, ZyeOfficeError):
        res = error_or_code.to_dict()
        if context:
            res["context"] = context
        return res
    elif isinstance(error_or_code, Exception):
        code = type(error_or_code).__name__.upper()
        msg = str(error_or_code)
        err = ZyeOfficeError(
            code=code,
            message=msg,
            app_name=app_name,
            operation_id=operation_id,
            retryable=retryable,
            remediation=remediation,
            details=details or ({"context": context} if context else None),
        )
        return err.to_dict()
    else:
        # error_or_code is string code
        code = error_or_code
        msg = message or ""
        err = ZyeOfficeError(
            code=code,
            message=msg,
            app_name=app_name,
            operation_id=operation_id,
            retryable=retryable,
            remediation=remediation,
            details=details or ({"context": context} if context else None),
        )
        return err.to_dict()
