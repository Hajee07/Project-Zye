"""
Zye AI — Retry & Circuit Breaker Engine (Day 17).
Provides bounded exponential backoff with jitter, circuit breaker state machine,
timeout execution wrappers, and idempotency classification.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Coroutine, Optional, Tuple, Type, Union

from zye_reliability.error_handler import CircuitOpenError, ZyeErrorCode, ZyeTimeoutError


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class RetryPolicy:
    max_retries: int = 3
    base_delay: float = 0.5
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    jitter: bool = True
    retryable_exceptions: Tuple[Type[BaseException], ...] = (
        ConnectionError,
        TimeoutError,
        OSError,
    )


# Common operations that mutate system state or perform side effects
NON_IDEMPOTENT_OPERATIONS: frozenset[str] = frozenset({
    "terminate_process",
    "request_process_termination",
    "empty_recycle_bin",
    "power_action",
    "shutdown_windows",
    "restart_windows",
    "send_whatsapp_message",
    "start_whatsapp_voice_call",
    "start_whatsapp_video_call",
    "end_whatsapp_call",
    "patch_own_code",
    "apply_code_patch",
    "rollback_code_backup",
    "delete_file",
    "delete_directory",
    "overwrite_file",
    "execute_emergency_reflex",
    "cyber_lockdown",
    "dictate_text_anywhere",
})


def is_idempotent_operation(tool_name: str) -> bool:
    """Return True if the operation is read-only or safe to repeat automatically."""
    norm = tool_name.strip().lower()
    for risky in NON_IDEMPOTENT_OPERATIONS:
        if risky in norm:
            return False
    # Standard read/inspect operations are idempotent
    safe_prefixes = ("get_", "list_", "inspect_", "read_", "check_", "search_", "preview_", "find_")
    return any(norm.startswith(p) for p in safe_prefixes)


class CircuitBreaker:
    """Standard Circuit Breaker pattern implementation with sliding window / threshold."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        self._update_state()
        return self._state

    def _update_state(self) -> None:
        now = time.time()
        if self._state == CircuitState.OPEN:
            if now - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0

    def can_execute(self) -> bool:
        """Check if execution is allowed through the circuit breaker."""
        self._update_state()
        return self._state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        """Record successful call outcome."""
        self._update_state()
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= 2:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record failed call outcome."""
        self._last_failure_time = time.time()
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
        elif self._state == CircuitState.CLOSED:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0


def calculate_backoff(attempt: int, policy: RetryPolicy) -> float:
    """Calculate exponential delay with optional jitter."""
    delay = policy.base_delay * (policy.backoff_factor ** attempt)
    delay = min(delay, policy.max_delay)
    if policy.jitter:
        jitter_amount = random.uniform(0.05, 0.25) * delay
        delay += jitter_amount
    return delay


def execute_with_retry(
    func: Callable[..., Any],
    policy: Optional[RetryPolicy] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute synchronous callable with retry policy and circuit breaker."""
    p = policy or RetryPolicy()
    cb = circuit_breaker

    if cb and not cb.can_execute():
        raise CircuitOpenError(f"Circuit breaker is {cb.state.value}. Execution blocked.")

    attempt = 0
    while True:
        try:
            res = func(*args, **kwargs)
            if cb:
                cb.record_success()
            return res
        except Exception as exc:
            if cb:
                cb.record_failure()

            if not isinstance(exc, p.retryable_exceptions) or attempt >= p.max_retries:
                raise

            delay = calculate_backoff(attempt, p)
            time.sleep(delay)
            attempt += 1


async def async_execute_with_retry(
    coro_fn: Callable[..., Coroutine[Any, Any, Any]],
    policy: Optional[RetryPolicy] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute asynchronous coroutine function with retry policy and circuit breaker."""
    p = policy or RetryPolicy()
    cb = circuit_breaker

    if cb and not cb.can_execute():
        raise CircuitOpenError(f"Circuit breaker is {cb.state.value}. Execution blocked.")

    attempt = 0
    while True:
        try:
            res = await coro_fn(*args, **kwargs)
            if cb:
                cb.record_success()
            return res
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if cb:
                cb.record_failure()

            if not isinstance(exc, p.retryable_exceptions) or attempt >= p.max_retries:
                raise

            delay = calculate_backoff(attempt, p)
            await asyncio.sleep(delay)
            attempt += 1


def execute_with_timeout(
    func: Callable[..., Any],
    timeout_seconds: float = 10.0,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute synchronous or asynchronous callable with a bounded timeout."""
    if inspect.iscoroutinefunction(func):
        async def _run() -> Any:
            return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
        try:
            loop = asyncio.get_running_loop()
            # If already running inside loop, schedule task
            future = asyncio.ensure_future(_run())
            return future
        except RuntimeError:
            return asyncio.run(_run())

    # Synchronous function execution via thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout_seconds)
        except concurrent.futures.TimeoutError as exc:
            raise ZyeTimeoutError(f"Function {getattr(func, '__name__', str(func))} timed out after {timeout_seconds}s") from exc
