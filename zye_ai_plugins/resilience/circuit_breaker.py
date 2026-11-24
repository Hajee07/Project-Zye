"""Enterprise 3-State Circuit Breaker for Zye AI Multi-AI Infrastructure (Day 27).

Implements the standard 3-state circuit breaker pattern per AI provider:
- CLOSED: Provider is healthy and accepting requests normally.
- OPEN: Provider is failing repeatedly; new requests are blocked immediately without network delay.
- HALF_OPEN: Cooldown duration elapsed; allows limited probe requests to verify recovery.

Enforces:
- Monotonic time calculation (immune to wall-clock skew)
- Per-provider isolation (one provider's outage never blocks others)
- Thread-safe state transitions
- Automatic cooldown recovery
- Full observability and state inspection
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("zye.ai_plugins.circuit_breaker")

# Standard Circuit Breaker States
STATE_CLOSED = "CLOSED"
STATE_OPEN = "OPEN"
STATE_HALF_OPEN = "HALF_OPEN"


class ProviderCircuitState:
    """State and transition tracker for a single AI provider."""

    def __init__(
        self,
        provider_id: str,
        failure_threshold: int = 3,
        open_duration_seconds: float = 30.0,
        recovery_threshold: int = 2,
        half_open_probes: int = 1,
    ):
        self.provider_id = provider_id
        self.failure_threshold = failure_threshold
        self.open_duration_seconds = open_duration_seconds
        self.recovery_threshold = recovery_threshold
        self.half_open_probes = half_open_probes

        self.state: str = STATE_CLOSED
        self.consecutive_failures: int = 0
        self.consecutive_successes: int = 0
        self.active_half_open_probes: int = 0
        self.last_state_change_time: float = time.monotonic()
        self.last_failure_time: Optional[float] = None
        self.last_failure_reason: Optional[str] = None
        self.total_trips: int = 0
        self._lock = threading.Lock()

    def check_permission(self) -> Tuple[bool, str]:
        """Check if a new request is permitted to reach the provider."""
        with self._lock:
            now = time.monotonic()

            if self.state == STATE_CLOSED:
                return True, "Circuit is CLOSED (Healthy)"

            if self.state == STATE_OPEN:
                elapsed = now - self.last_state_change_time
                if elapsed >= self.open_duration_seconds:
                    # Transition to HALF_OPEN
                    self.state = STATE_HALF_OPEN
                    self.active_half_open_probes = 1
                    self.consecutive_successes = 0
                    self.last_state_change_time = now
                    logger.info(
                        "Circuit for provider '%s' transitioned from OPEN to HALF_OPEN after %.1fs cooldown.",
                        self.provider_id,
                        elapsed,
                    )
                    return True, "Circuit entered HALF_OPEN (Probe allowed)"
                remaining = self.open_duration_seconds - elapsed
                return False, f"Circuit is OPEN (Blocked for next {remaining:.1f}s: {self.last_failure_reason or 'repeated failures'})"

            if self.state == STATE_HALF_OPEN:
                if self.active_half_open_probes < self.half_open_probes:
                    self.active_half_open_probes += 1
                    return True, "Circuit is HALF_OPEN (Probe slot granted)"
                return False, "Circuit is HALF_OPEN (All probe slots currently in-flight)"

            return True, "Circuit permitted"

    def record_success(self) -> None:
        """Record a successful request."""
        with self._lock:
            now = time.monotonic()
            if self.state == STATE_HALF_OPEN:
                self.consecutive_successes += 1
                if self.active_half_open_probes > 0:
                    self.active_half_open_probes -= 1

                if self.consecutive_successes >= self.recovery_threshold:
                    self.state = STATE_CLOSED
                    self.consecutive_failures = 0
                    self.last_state_change_time = now
                    logger.info(
                        "Circuit for provider '%s' fully RECOVERED -> CLOSED after %d consecutive successes.",
                        self.provider_id,
                        self.consecutive_successes,
                    )
            elif self.state == STATE_CLOSED:
                # Reset failure counter on fresh success
                self.consecutive_failures = 0

    def record_failure(self, reason: str = "") -> None:
        """Record an operational/transport failure."""
        with self._lock:
            now = time.monotonic()
            self.last_failure_time = now
            self.last_failure_reason = reason or "Unknown operational failure"

            if self.state == STATE_HALF_OPEN:
                # Probe failed, immediately re-open
                self.state = STATE_OPEN
                self.total_trips += 1
                self.consecutive_successes = 0
                self.active_half_open_probes = 0
                self.last_state_change_time = now
                logger.warning(
                    "Circuit for provider '%s' probe failed: '%s'. Re-opened circuit for %.1fs.",
                    self.provider_id,
                    reason,
                    self.open_duration_seconds,
                )
            elif self.state == STATE_CLOSED:
                self.consecutive_failures += 1
                if self.consecutive_failures >= self.failure_threshold:
                    self.state = STATE_OPEN
                    self.total_trips += 1
                    self.last_state_change_time = now
                    logger.warning(
                        "Circuit for provider '%s' TRIPPED to OPEN after %d consecutive failures. Reason: %s",
                        self.provider_id,
                        self.consecutive_failures,
                        reason,
                    )

    def manual_open(self, reason: str = "Admin manual trip") -> None:
        with self._lock:
            self.state = STATE_OPEN
            self.total_trips += 1
            self.last_failure_reason = reason
            self.last_state_change_time = time.monotonic()

    def manual_close(self) -> None:
        with self._lock:
            self.state = STATE_CLOSED
            self.consecutive_failures = 0
            self.consecutive_successes = 0
            self.active_half_open_probes = 0
            self.last_state_change_time = time.monotonic()

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            elapsed = time.monotonic() - self.last_state_change_time
            time_until_retry = max(0.0, self.open_duration_seconds - elapsed) if self.state == STATE_OPEN else 0.0
            return {
                "provider_id": self.provider_id,
                "state": self.state,
                "consecutive_failures": self.consecutive_failures,
                "consecutive_successes": self.consecutive_successes,
                "failure_threshold": self.failure_threshold,
                "open_duration_seconds": self.open_duration_seconds,
                "time_until_retry_seconds": round(time_until_retry, 2),
                "total_trips": self.total_trips,
                "last_failure_reason": self.last_failure_reason,
            }


class CircuitBreakerRegistry:
    """Singleton registry managing circuit breakers for all providers."""

    _instance: Optional[CircuitBreakerRegistry] = None
    _lock = threading.Lock()

    def __init__(self):
        self._circuits: Dict[str, ProviderCircuitState] = {}
        self._default_threshold = 3
        self._default_open_duration = 30.0

    @classmethod
    def get_instance(cls) -> CircuitBreakerRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_circuit(self, provider_id: str) -> ProviderCircuitState:
        pid = provider_id.lower().strip()
        if pid not in self._circuits:
            with self._lock:
                if pid not in self._circuits:
                    self._circuits[pid] = ProviderCircuitState(
                        provider_id=pid,
                        failure_threshold=self._default_threshold,
                        open_duration_seconds=self._default_open_duration,
                    )
        return self._circuits[pid]

    def record_success(self, provider_id: str) -> None:
        self.get_circuit(provider_id).record_success()

    def record_failure(self, provider_id: str, reason: str = "") -> None:
        self.get_circuit(provider_id).record_failure(reason)

    def check_permission(self, provider_id: str) -> Tuple[bool, str]:
        return self.get_circuit(provider_id).check_permission()

    def get_circuit_state(self, provider_id: str) -> str:
        return self.get_circuit(provider_id).state

    def reset_circuit(self, provider_id: str) -> None:
        self.get_circuit(provider_id).manual_close()

    def trip_circuit(self, provider_id: str, reason: str = "Admin tripped") -> None:
        self.get_circuit(provider_id).manual_open(reason)

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        return {pid: circuit.to_dict() for pid, circuit in self._circuits.items()}


# Global convenience accessors
def get_circuit_breaker() -> CircuitBreakerRegistry:
    return CircuitBreakerRegistry.get_instance()
