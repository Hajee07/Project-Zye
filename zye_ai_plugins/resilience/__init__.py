"""Resilience Subsystem for Zye AI (Day 27).

Exports:
- Circuit Breaker (3-state: CLOSED, OPEN, HALF_OPEN)
- Retry Policy (Full Jitter, Exponential Backoff, Error Classification)
- Rate Limiter (Token Bucket, RPM/TPM limits, Cooldowns)
- Concurrency Controller (Adaptive AIMD, Bounded Slots)
- Bulkhead Manager (Integrated Isolation)
"""

from .bulkhead import BulkheadManager, FailoverEvent, get_bulkhead_manager
from .circuit_breaker import (
    STATE_CLOSED,
    STATE_HALF_OPEN,
    STATE_OPEN,
    CircuitBreakerRegistry,
    ProviderCircuitState,
    get_circuit_breaker,
)
from .concurrency_controller import (
    ConcurrencyControllerRegistry,
    ProviderConcurrencyPool,
    get_concurrency_controller,
)
from .rate_limiter import (
    ProviderRateLimiter,
    RateLimiterRegistry,
    get_rate_limiter,
)
from .retry_policy import (
    calculate_retry_delay,
    classify_provider_error,
    execute_with_retry,
    extract_retry_after,
)

__all__ = [
    "STATE_CLOSED",
    "STATE_OPEN",
    "STATE_HALF_OPEN",
    "ProviderCircuitState",
    "CircuitBreakerRegistry",
    "get_circuit_breaker",
    "classify_provider_error",
    "calculate_retry_delay",
    "extract_retry_after",
    "execute_with_retry",
    "ProviderRateLimiter",
    "RateLimiterRegistry",
    "get_rate_limiter",
    "ProviderConcurrencyPool",
    "ConcurrencyControllerRegistry",
    "get_concurrency_controller",
    "FailoverEvent",
    "BulkheadManager",
    "get_bulkhead_manager",
]
