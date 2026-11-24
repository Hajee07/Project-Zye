"""
Zye AI — Reliability & Robustness Subsystem (Day 17).
Provides enterprise-grade error taxonomy, input validation schemas,
retry controllers, circuit breaking, telemetry aggregation, and crash recovery.
"""

from __future__ import annotations

from zye_reliability.error_handler import (
    AccessDeniedError,
    CircuitOpenError,
    InputValidationError,
    ProcessNotFoundError,
    ProtectedProcessError,
    TANGLISH_MESSAGES,
    ZyeError,
    ZyeErrorCode,
    ZyeErrorResponse,
    ZyeTimeoutError,
    build_zye_error_response,
    classify_exception,
    format_user_friendly_error,
    redact_error_details,
)
from zye_reliability.input_validator import (
    ValidatedAppName,
    ValidatedBrightnessLevel,
    ValidatedPID,
    ValidatedPath,
    ValidatedScrollAmount,
    ValidatedSearchQuery,
    ValidatedVolumeLevel,
    validate_app_name,
    validate_brightness,
    validate_path,
    validate_pid,
    validate_scroll_amount,
    validate_search_query,
    validate_volume,
)
from zye_reliability.recovery_manager import ApplicationRecoveryManager
from zye_reliability.retry_manager import (
    CircuitBreaker,
    CircuitState,
    NON_IDEMPOTENT_OPERATIONS,
    RetryPolicy,
    async_execute_with_retry,
    execute_with_retry,
    execute_with_timeout,
    is_idempotent_operation,
)
from zye_reliability.telemetry import (
    CorrelationContext,
    ZyeTelemetryLogger,
)

__all__ = [
    # Error Handling
    "AccessDeniedError",
    "CircuitOpenError",
    "InputValidationError",
    "ProcessNotFoundError",
    "ProtectedProcessError",
    "TANGLISH_MESSAGES",
    "ZyeError",
    "ZyeErrorCode",
    "ZyeErrorResponse",
    "ZyeTimeoutError",
    "build_zye_error_response",
    "classify_exception",
    "format_user_friendly_error",
    "redact_error_details",
    # Input Validation
    "ValidatedAppName",
    "ValidatedBrightnessLevel",
    "ValidatedPID",
    "ValidatedPath",
    "ValidatedScrollAmount",
    "ValidatedSearchQuery",
    "ValidatedVolumeLevel",
    "validate_app_name",
    "validate_brightness",
    "validate_path",
    "validate_pid",
    "validate_scroll_amount",
    "validate_search_query",
    "validate_volume",
    # Recovery
    "ApplicationRecoveryManager",
    # Retry & Circuit Breaker
    "CircuitBreaker",
    "CircuitState",
    "NON_IDEMPOTENT_OPERATIONS",
    "RetryPolicy",
    "async_execute_with_retry",
    "execute_with_retry",
    "execute_with_timeout",
    "is_idempotent_operation",
    # Telemetry
    "CorrelationContext",
    "ZyeTelemetryLogger",
]
