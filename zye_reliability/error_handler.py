"""
Zye AI — Reliability & Advanced Error Handling Engine (Day 17).
Provides structured exception hierarchy, standardized error envelopes, secret sanitization,
exception classification, and bilingual/Tanglish user-friendly explanations.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


class ZyeErrorCode(str, Enum):
    INVALID_INPUT = "INVALID_INPUT"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    PROCESS_NOT_FOUND = "PROCESS_NOT_FOUND"
    ACCESS_DENIED = "ACCESS_DENIED"
    PROTECTED_PROCESS = "PROTECTED_PROCESS"
    PID_REUSE_DETECTED = "PID_REUSE_DETECTED"
    TIMEOUT = "TIMEOUT"
    OPERATION_FAILED = "OPERATION_FAILED"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Secret redaction patterns
_SECRET_PATTERNS = [
    (re.compile(r"AIza[0-9A-Za-z_-]{30,}"), "[REDACTED_GEMINI_KEY]"),
    (re.compile(r"sk-[a-zA-Z0-9_-]{20,}"), "[REDACTED_API_KEY]"),
    (re.compile(r"ghp_[a-zA-Z0-9]{30,}"), "[REDACTED_GITHUB_KEY]"),
    (re.compile(r"(?i)(api[_-]?key|token|password|secret|auth|credential)\s*[:=]\s*['\"]?[^\s'\"]+['\"]?"), r"\1=[REDACTED]"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
]


def redact_error_details(text: str) -> str:
    """Sanitize strings by stripping out API keys, tokens, and credentials."""
    if not text:
        return ""
    result = str(text)
    for pattern, replacement in _SECRET_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


# Tanglish user-friendly messages for TTS and conversational voice output
TANGLISH_MESSAGES: dict[ZyeErrorCode, str] = {
    ZyeErrorCode.INVALID_INPUT: "Input thappa irukku pa, sariya check panni anupunga.",
    ZyeErrorCode.VALIDATION_FAILED: "Input validation fail aayiduchu, data format sariya illai.",
    ZyeErrorCode.PROCESS_NOT_FOUND: "Andha process kedaikala boss! App running-ah nu check pannunga.",
    ZyeErrorCode.ACCESS_DENIED: "Access denied boss! Administrator permission theva.",
    ZyeErrorCode.PROTECTED_PROCESS: "Idhu Windows system process pa! Idhai terminate panna mudiyaadhu.",
    ZyeErrorCode.PID_REUSE_DETECTED: "Process ID maari pochu, pazhaya process ippo illa.",
    ZyeErrorCode.TIMEOUT: "Operation timeout aayiruchu pa, konjam neram kazhichu try pannunga.",
    ZyeErrorCode.OPERATION_FAILED: "Vela mudiyala boss, operation failed.",
    ZyeErrorCode.CIRCUIT_OPEN: "Thodarnthu thappu nadandhadhaala system temporary-ah pause panni irukku.",
    ZyeErrorCode.RECOVERY_FAILED: "App recovery panna mudiyala pa.",
    ZyeErrorCode.RESOURCE_UNAVAILABLE: "System resource pathala, konjam wait pannunga.",
    ZyeErrorCode.APPROVAL_REQUIRED: "Idhu risk-aana operation, unga confirmation theva.",
    ZyeErrorCode.INTERNAL_ERROR: "Ulla edho problem aayiduchu, error log-ah paarunga.",
}


@dataclass
class ZyeErrorResponse:
    """Structured, standardized error response envelope."""
    status: str = "error"
    code: str = ZyeErrorCode.INTERNAL_ERROR.value
    message: str = ""
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    retryable: bool = False
    next_step: str = ""
    tanglish_message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["message"] = redact_error_details(d["message"])
        return d


class ZyeError(Exception):
    """Base exception for all Zye operations."""

    def __init__(
        self,
        message: str,
        code: ZyeErrorCode = ZyeErrorCode.INTERNAL_ERROR,
        trace_id: Optional[str] = None,
        retryable: bool = False,
        next_step: str = "",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = redact_error_details(message)
        self.trace_id = trace_id or uuid.uuid4().hex[:12]
        self.retryable = retryable
        self.next_step = next_step
        self.details = details or {}

    def to_response(self) -> ZyeErrorResponse:
        tanglish = TANGLISH_MESSAGES.get(self.code, "Operation-il oru error vandhuduchu.")
        return ZyeErrorResponse(
            status="error",
            code=self.code.value,
            message=self.message,
            trace_id=self.trace_id,
            retryable=self.retryable,
            next_step=self.next_step,
            tanglish_message=tanglish,
            details=self.details,
        )


class ProcessNotFoundError(ZyeError):
    def __init__(self, message: str = "Process not found", **kwargs: Any) -> None:
        kwargs.setdefault("code", ZyeErrorCode.PROCESS_NOT_FOUND)
        kwargs.setdefault("next_step", "Verify the process name or PID is currently running.")
        super().__init__(message, **kwargs)


class AccessDeniedError(ZyeError):
    def __init__(self, message: str = "Access denied", **kwargs: Any) -> None:
        kwargs.setdefault("code", ZyeErrorCode.ACCESS_DENIED)
        kwargs.setdefault("next_step", "Check permissions or run with elevated credentials.")
        super().__init__(message, **kwargs)


class ProtectedProcessError(ZyeError):
    def __init__(self, message: str = "Target is a protected Windows system process", **kwargs: Any) -> None:
        kwargs.setdefault("code", ZyeErrorCode.PROTECTED_PROCESS)
        kwargs.setdefault("next_step", "Protected system processes cannot be terminated.")
        super().__init__(message, **kwargs)


class ZyeTimeoutError(ZyeError):
    def __init__(self, message: str = "Operation timed out", **kwargs: Any) -> None:
        kwargs.setdefault("code", ZyeErrorCode.TIMEOUT)
        kwargs.setdefault("retryable", True)
        kwargs.setdefault("next_step", "Retry with a higher timeout or wait for system load to drop.")
        super().__init__(message, **kwargs)


class CircuitOpenError(ZyeError):
    def __init__(self, message: str = "Circuit breaker is OPEN", **kwargs: Any) -> None:
        kwargs.setdefault("code", ZyeErrorCode.CIRCUIT_OPEN)
        kwargs.setdefault("next_step", "Wait for the circuit breaker recovery timeout to expire.")
        super().__init__(message, **kwargs)


class InputValidationError(ZyeError):
    def __init__(self, message: str = "Input validation failed", **kwargs: Any) -> None:
        kwargs.setdefault("code", ZyeErrorCode.VALIDATION_FAILED)
        kwargs.setdefault("next_step", "Check argument types, ranges, and formatting.")
        super().__init__(message, **kwargs)


def classify_exception(exc: BaseException) -> ZyeErrorCode:
    """Map standard Python and system exceptions to ZyeErrorCode."""
    if isinstance(exc, ZyeError):
        return exc.code
    if isinstance(exc, (ValueError, TypeError)):
        return ZyeErrorCode.INVALID_INPUT
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return ZyeErrorCode.TIMEOUT
    if isinstance(exc, PermissionError):
        return ZyeErrorCode.ACCESS_DENIED
    if isinstance(exc, FileNotFoundError):
        return ZyeErrorCode.RESOURCE_UNAVAILABLE
    if isinstance(exc, ConnectionError):
        return ZyeErrorCode.RESOURCE_UNAVAILABLE
    return ZyeErrorCode.INTERNAL_ERROR


def build_zye_error_response(
    code: ZyeErrorCode | str,
    message: str,
    *,
    trace_id: Optional[str] = None,
    retryable: bool = False,
    next_step: str = "",
    details: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Helper to construct a standardized dictionary error response."""
    if isinstance(code, str):
        try:
            err_code = ZyeErrorCode(code)
        except ValueError:
            err_code = ZyeErrorCode.INTERNAL_ERROR
    else:
        err_code = code

    tanglish = TANGLISH_MESSAGES.get(err_code, "Operation-il oru error vandhuduchu.")
    resp = ZyeErrorResponse(
        status="error",
        code=err_code.value,
        message=redact_error_details(message),
        trace_id=trace_id or uuid.uuid4().hex[:12],
        retryable=retryable,
        next_step=next_step,
        tanglish_message=tanglish,
        details=details or {},
    )
    return resp.to_dict()


def format_user_friendly_error(error_resp: dict[str, Any]) -> str:
    """Format an error dict into a conversational, user-facing voice prompt."""
    tanglish = error_resp.get("tanglish_message")
    if tanglish:
        return tanglish
    msg = error_resp.get("message", "An error occurred.")
    return f"Sorry boss, error vandhuduchu: {msg}"
