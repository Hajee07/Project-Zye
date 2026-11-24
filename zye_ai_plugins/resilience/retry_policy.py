"""Advanced Request Retry Engine with Full Jitter and Error Classification (Day 27).

Provides robust retry capabilities for AI provider API calls:
- Strict Error Classification: Distinguishes transient (network, 429, 503) from permanent (401, 403, 400)
- Exponential Backoff with Full Jitter to prevent thundering herd problems
- Explicit Retry-After header support
- Maximum retry limits and overall request deadline enforcement
- Circuit-breaker integration
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple, TypeVar

from .circuit_breaker import get_circuit_breaker

logger = logging.getLogger("zye.ai_plugins.retry")

T = TypeVar("T")

# HTTP Status Codes
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404, 405, 422}


def classify_provider_error(
    status_code: Optional[int] = None,
    error_message: str = "",
    exception: Optional[Exception] = None,
) -> Tuple[bool, str]:
    """Classify an error into (is_retryable, error_category).

    Returns:
        (True, "TRANSIENT_NETWORK" | "RATE_LIMITED" | "SERVER_OVERLOAD") if safe to retry.
        (False, "AUTH_ERROR" | "CLIENT_ERROR" | "INVALID_REQUEST" | "FATAL") if retry should be aborted.
    """
    msg = (error_message or (str(exception) if exception else "")).lower()

    # Check status code first
    if status_code is not None:
        if status_code == 429:
            return True, "RATE_LIMITED"
        if status_code in (502, 503, 504):
            return True, "SERVER_OVERLOAD"
        if status_code in (408, 500):
            return True, "TRANSIENT_SERVER_ERROR"
        if status_code in (401, 403):
            return False, "AUTH_ERROR"
        if status_code in NON_RETRYABLE_STATUS_CODES:
            return False, "CLIENT_ERROR"

    # Inspect textual patterns
    if any(k in msg for k in ("unauthorized", "invalid_api_key", "authentication", "forbidden", "permission denied")):
        return False, "AUTH_ERROR"
    if any(k in msg for k in ("model_not_found", "invalid model", "does not exist", "unsupported")):
        return False, "INVALID_MODEL"
    if any(k in msg for k in ("ssrf", "blocked private ip", "loopback forbidden")):
        return False, "SECURITY_BLOCKED"
    if any(k in msg for k in ("rate limit", "quota exceeded", "too many requests", "429")):
        return True, "RATE_LIMITED"
    if any(k in msg for k in ("timeout", "timed out", "connection reset", "connection refused", "broken pipe", "network")):
        return True, "TRANSIENT_NETWORK"
    if any(k in msg for k in ("502", "503", "504", "overloaded", "capacity")):
        return True, "SERVER_OVERLOAD"

    return False, "UNKNOWN_ERROR"


def extract_retry_after(error_message: str, headers: Optional[Dict[str, str]] = None) -> Optional[float]:
    """Extract Retry-After duration in seconds from headers or error message."""
    if headers:
        for k, v in headers.items():
            if k.lower() == "retry-after":
                try:
                    return max(0.5, float(v.strip()))
                except ValueError:
                    pass

    # Regex search in error text: "retry after 3.5 seconds" or "try again in 2s"
    match = re.search(r"(?:retry after|try again in|wait)\s*([0-9]+(?:\.[0-9]+)?)\s*s", error_message.lower())
    if match:
        try:
            return max(0.5, float(match.group(1)))
        except ValueError:
            pass

    return None


def calculate_retry_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    retry_after: Optional[float] = None,
) -> float:
    """Calculate exponential backoff with full jitter, honoring Retry-After when available."""
    if retry_after is not None and retry_after > 0:
        return min(max_delay, retry_after)

    # Full jitter: backoff = random between 0 and min(max_delay, base_delay * 2^attempt)
    raw_backoff = min(max_delay, base_delay * (2 ** attempt))
    jittered_delay = random.uniform(base_delay * 0.5, raw_backoff)
    return round(jittered_delay, 3)


async def execute_with_retry(
    provider_id: str,
    operation_fn: Callable[[], Coroutine[Any, Any, T]],
    max_retries: int = 2,
    base_delay: float = 1.0,
    max_delay: float = 8.0,
    overall_deadline_seconds: float = 40.0,
) -> T:
    """Execute an async operation with intelligent retry and circuit breaker updates.

    Raises the final exception or returns the operation result.
    """
    cb = get_circuit_breaker()
    start_time = time.monotonic()
    last_exc: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        # 1. Check Circuit Breaker Permission
        permitted, reason = cb.check_permission(provider_id)
        if not permitted:
            logger.warning("Request to '%s' blocked by circuit breaker: %s", provider_id, reason)
            raise RuntimeError(f"Circuit breaker blocked request to '{provider_id}': {reason}")

        # 2. Check overall deadline
        if time.monotonic() - start_time >= overall_deadline_seconds:
            logger.warning("Operation for '%s' aborted due to overall deadline expiration.", provider_id)
            cb.record_failure(provider_id, "Overall request deadline exceeded")
            raise TimeoutError(f"Request to '{provider_id}' exceeded overall deadline of {overall_deadline_seconds}s")

        try:
            result = await operation_fn()

            # Inspect result if it has an error status
            status = getattr(result, "status", None)
            if status == "error":
                err_msg = getattr(result, "error_message", "Provider returned error status")
                is_retryable, category = classify_provider_error(error_message=err_msg)

                if is_retryable and attempt < max_retries:
                    retry_after = extract_retry_after(err_msg)
                    delay = calculate_retry_delay(attempt, base_delay, max_delay, retry_after)
                    logger.warning(
                        "Provider '%s' returned %s (attempt %d/%d). Retrying in %.2fs. Error: %s",
                        provider_id,
                        category,
                        attempt + 1,
                        max_retries,
                        delay,
                        err_msg,
                    )
                    await asyncio.sleep(delay)
                    continue

                # Permanent failure or out of retries
                cb.record_failure(provider_id, f"{category}: {err_msg}")
                return result

            # Operation succeeded
            cb.record_success(provider_id)
            return result

        except Exception as exc:
            last_exc = exc
            is_retryable, category = classify_provider_error(exception=exc)

            if not is_retryable or attempt >= max_retries:
                cb.record_failure(provider_id, f"{category}: {exc}")
                logger.error(
                    "Provider '%s' failed permanently (attempt %d/%d, category=%s): %s",
                    provider_id,
                    attempt + 1,
                    max_retries,
                    category,
                    exc,
                )
                raise exc

            retry_after = extract_retry_after(str(exc))
            delay = calculate_retry_delay(attempt, base_delay, max_delay, retry_after)
            logger.warning(
                "Provider '%s' encountered %s: %s. Retrying in %.2fs (attempt %d/%d)...",
                provider_id,
                category,
                exc,
                delay,
                attempt + 1,
                max_retries,
            )
            await asyncio.sleep(delay)

    if last_exc:
        raise last_exc
    raise RuntimeError(f"Retry attempts exhausted for provider '{provider_id}'")
