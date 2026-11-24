"""
ZYE AI — Gemini 503 Recovery Engine & Error Classifier
======================================================

Implements Section 08 & Section 09 of Master Engineering Specification.
Classifies errors into deterministic failure types vs transient overload,
applies exponential backoff with jitter, integrates with ModelCircuitBreaker,
and strictly enforces that 503 overload NEVER blindly rotates all 7 Gemini keys.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Coroutine, Optional, TypeVar

from zye_core.event_bus import ZyeEventBus
from zye_core.types import ExecutionOutcome, ZyeEvent, ZyeEventType
from zye_intelligence.circuit_breaker import ModelCircuitBreaker

logger = logging.getLogger("zye.intelligence.recovery")

T = TypeVar("T")


class ErrorCategory(str, Enum):
    """Classification of errors returned by LLM Gateways."""

    TRANSIENT_503 = "TRANSIENT_503"      # Model overloaded / service unavailable
    RATE_LIMIT_429 = "RATE_LIMIT_429"    # Account/key quota or rate limit exceeded
    CLIENT_400 = "CLIENT_400"            # Invalid argument, bad schema, non-retryable
    AUTH_401_403 = "AUTH_401_403"        # Invalid key, permission denied
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"  # TCP timeout, socket hangup
    UNKNOWN = "UNKNOWN"                  # Unclassified exceptions


@dataclass(slots=True)
class RecoveryDecision:
    """Deterministic routing decision for an encountered gateway error."""

    category: ErrorCategory
    retryable: bool
    rotate_key: bool
    trip_circuit: bool
    reason: str


class GeminiRecoveryEngine:
    """
    Intelligent failure recovery engine for Gemini Master Brain.
    Manages retry loops, backoff calculation, key rotation gating,
    and circuit breaker coordination.
    """

    def __init__(
        self,
        circuit_breaker: Optional[ModelCircuitBreaker] = None,
        event_bus: Optional[ZyeEventBus] = None,
        base_backoff: float = 1.0,
        max_backoff: float = 10.0,
        jitter_max: float = 0.5,
    ) -> None:
        self.circuit_breaker = circuit_breaker or ModelCircuitBreaker()
        self.event_bus = event_bus
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff
        self.jitter_max = jitter_max

    def classify_error(self, exc: Exception) -> RecoveryDecision:
        """
        Classifies an exception into actionable recovery guidance.
        Enforces key policy: 503 Overload is model-level, NOT key-level.
        Never rotate all 7 keys on model overload!
        """
        err_msg = str(exc).lower()
        err_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        code_val = None
        if err_code is not None:
            try:
                code_val = int(getattr(err_code, "value", err_code))
            except (ValueError, TypeError):
                code_val = None

        # 1. Check for 503 / Service Unavailable / Model Overloaded
        if (
            code_val == 503
            or "503" in err_msg
            or "unavailable" in err_msg
            or "overloaded" in err_msg
            or "server is temporarily overloaded" in err_msg
            or "resource exhausted" in err_msg and "model" in err_msg
        ):
            return RecoveryDecision(
                category=ErrorCategory.TRANSIENT_503,
                retryable=True,
                rotate_key=False,  # CRITICAL: Overload is server-side; rotating keys wastes quota across all keys!
                trip_circuit=True,
                reason="Model overloaded (503). Retrying with backoff; key rotation withheld.",
            )

        # 2. Check for 429 / Rate Limit / Quota Exceeded
        if (
            code_val == 429
            or "429" in err_msg
            or "rate limit" in err_msg
            or "quota" in err_msg
            or "resource_exhausted" in err_msg
        ):
            return RecoveryDecision(
                category=ErrorCategory.RATE_LIMIT_429,
                retryable=True,
                rotate_key=True,  # Rotate to next key in 7-key manager pool
                trip_circuit=False,
                reason="Key quota exhausted (429). Rotating to next API key.",
            )

        # 3. Check for 400 / Invalid Argument / Bad Schema
        if (
            code_val == 400
            or "400" in err_msg
            or "invalid argument" in err_msg
            or "bad request" in err_msg
            or "schema" in err_msg
            or "additionalproperties" in err_msg
        ):
            return RecoveryDecision(
                category=ErrorCategory.CLIENT_400,
                retryable=False,  # Deterministic failure: fail-fast!
                rotate_key=False,
                trip_circuit=False,
                reason="Client request invalid (400). Immediate fail-fast without retry.",
            )

        # 4. Check for 401 / 403 Authentication / Permission
        if (
            code_val in (401, 403)
            or "401" in err_msg
            or "403" in err_msg
            or "permission denied" in err_msg
            or "unauthenticated" in err_msg
            or "api key not valid" in err_msg
        ):
            return RecoveryDecision(
                category=ErrorCategory.AUTH_401_403,
                retryable=True,
                rotate_key=True,
                trip_circuit=False,
                reason="API key unauthorized (401/403). Rotating API key.",
            )

        # 5. Check for Network / Timeout
        if (
            "timeout" in err_msg
            or "timed out" in err_msg
            or "deadline exceeded" in err_msg
            or "connection reset" in err_msg
        ):
            return RecoveryDecision(
                category=ErrorCategory.NETWORK_TIMEOUT,
                retryable=True,
                rotate_key=False,
                trip_circuit=True,
                reason="Network timeout. Retrying with backoff.",
            )

        # Default unknown
        return RecoveryDecision(
            category=ErrorCategory.UNKNOWN,
            retryable=False,
            rotate_key=False,
            trip_circuit=False,
            reason=f"Unclassified exception: {type(exc).__name__}",
        )

    def calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with random jitter."""
        backoff = min(self.max_backoff, self.base_backoff * (2 ** attempt))
        jitter = random.uniform(0.0, self.jitter_max)
        return backoff + jitter

    async def execute_with_recovery(
        self,
        model_id: str,
        operation: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        max_retries: int = 3,
        key_rotator: Optional[Callable[[], None]] = None,
        **kwargs: Any,
    ) -> T:
        """
        Execute an async Gemini operation with circuit breaker and recovery policy.
        """
        # 1. Gate check via circuit breaker
        if not self.circuit_breaker.allow_request(model_id):
            msg = f"Circuit breaker OPEN for model '{model_id}'. Request rejected."
            logger.warning(msg)
            if self.event_bus:
                self.event_bus.publish_sync(
                    ZyeEvent(
                        event_type=ZyeEventType.MODEL_CIRCUIT_TRIPPED,
                        payload={"model_id": model_id, "reason": msg},
                    )
                )
            raise RuntimeError(msg)

        last_exception: Optional[Exception] = None

        for attempt in range(max_retries):
            try:
                result = await operation(*args, **kwargs)
                # Success -> record in circuit breaker
                self.circuit_breaker.record_success(model_id)
                return result
            except Exception as exc:
                last_exception = exc
                decision = self.classify_error(exc)
                logger.warning(
                    "Gateway call to %s failed (attempt %d/%d): %s | Decision: %s",
                    model_id,
                    attempt + 1,
                    max_retries,
                    exc,
                    decision.reason,
                )

                if decision.trip_circuit:
                    self.circuit_breaker.record_transient_failure(model_id)

                if not decision.retryable:
                    logger.error("Non-retryable error encountered (%s). Failing fast.", decision.category.value)
                    raise

                if decision.rotate_key and key_rotator is not None:
                    logger.info("Executing API key rotation for %s...", decision.category.value)
                    key_rotator()

                if attempt < max_retries - 1:
                    sleep_time = self.calculate_backoff(attempt)
                    logger.info("Backing off for %0.2fs before attempt %d...", sleep_time, attempt + 2)
                    await asyncio.sleep(sleep_time)

        if last_exception:
            raise last_exception
        raise RuntimeError("Gateway operation failed after retries exhausted")

    def execute_with_recovery_sync(
        self,
        model_id: str,
        operation: Callable[..., T],
        *args: Any,
        max_retries: int = 3,
        key_rotator: Optional[Callable[[], None]] = None,
        **kwargs: Any,
    ) -> T:
        """Synchronous wrapper for execute_with_recovery."""
        if not self.circuit_breaker.allow_request(model_id):
            raise RuntimeError(f"Circuit breaker OPEN for model '{model_id}'. Request rejected.")

        last_exception: Optional[Exception] = None

        for attempt in range(max_retries):
            try:
                result = operation(*args, **kwargs)
                self.circuit_breaker.record_success(model_id)
                return result
            except Exception as exc:
                last_exception = exc
                decision = self.classify_error(exc)

                if decision.trip_circuit:
                    self.circuit_breaker.record_transient_failure(model_id)

                if not decision.retryable:
                    raise

                if decision.rotate_key and key_rotator is not None:
                    key_rotator()

                if attempt < max_retries - 1:
                    sleep_time = self.calculate_backoff(attempt)
                    time.sleep(sleep_time)

        if last_exception:
            raise last_exception
        raise RuntimeError("Gateway operation failed after retries exhausted")


__all__ = [
    "ErrorCategory",
    "RecoveryDecision",
    "GeminiRecoveryEngine",
]
