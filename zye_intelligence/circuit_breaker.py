"""
ZYE AI — Intelligent Model Circuit Breaker
==========================================

Implements Section 08 & Section 09 of Master Engineering Specification.
Safeguards Gemini Gateway against repeating 503 transient failures,
providing exponential backoff, circuit tripping, and controlled half-open probes.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

from zye_core.types import ModelCircuitState

logger = logging.getLogger("zye.intelligence.circuit_breaker")


@dataclass
class CircuitMetrics:
    failure_threshold: int = 3
    cooldown_seconds: float = 30.0
    failures: int = 0
    opened_at: Optional[float] = None
    probe_in_flight: bool = False
    state: ModelCircuitState = ModelCircuitState.CLOSED

    def allow_request(self) -> bool:
        """Evaluate if an outbound request is permitted through the circuit."""
        now = time.monotonic()
        if self.state == ModelCircuitState.CLOSED:
            return True

        if self.state == ModelCircuitState.OPEN:
            if self.opened_at is None:
                self.opened_at = now
            elapsed = now - self.opened_at
            if elapsed < self.cooldown_seconds:
                # Still within cooldown window
                return False

            # Cooldown elapsed -> transition to HALF_OPEN for 1 probe
            self.state = ModelCircuitState.HALF_OPEN
            self.probe_in_flight = True
            logger.info("Circuit breaker entering HALF_OPEN probe state after %0.1fs cooldown", elapsed)
            return True

        if self.state == ModelCircuitState.HALF_OPEN:
            # Only single probe permitted in flight
            if self.probe_in_flight:
                return False
            self.probe_in_flight = True
            return True

        return True

    def record_success(self) -> None:
        """Reset failures and close circuit upon verified successful operation."""
        self.failures = 0
        self.opened_at = None
        self.probe_in_flight = False
        self.state = ModelCircuitState.CLOSED

    def record_transient_failure(self) -> None:
        """Record transient failure (e.g. 503 Overload). Trip circuit if threshold reached."""
        self.failures += 1
        now = time.monotonic()

        if self.state == ModelCircuitState.HALF_OPEN or self.failures >= self.failure_threshold:
            self.state = ModelCircuitState.OPEN
            self.opened_at = now
            self.probe_in_flight = False
            logger.warning(
                "Circuit breaker TRIPPED to OPEN state! Failures=%d (threshold=%d), cooldown=%0.1fs",
                self.failures,
                self.failure_threshold,
                self.cooldown_seconds,
            )
        else:
            self.probe_in_flight = False


class ModelCircuitBreaker:
    """Thread-safe circuit breaker registry partitioned by model identifier."""

    def __init__(
        self,
        default_failure_threshold: int = 3,
        default_cooldown_seconds: float = 30.0,
    ) -> None:
        self.default_threshold = default_failure_threshold
        self.default_cooldown = default_cooldown_seconds
        self._circuits: Dict[str, CircuitMetrics] = {}
        self._lock = threading.Lock()

    def _get_circuit(self, model_id: str) -> CircuitMetrics:
        if model_id not in self._circuits:
            self._circuits[model_id] = CircuitMetrics(
                failure_threshold=self.default_threshold,
                cooldown_seconds=self.default_cooldown,
            )
        return self._circuits[model_id]

    def allow_request(self, model_id: str) -> bool:
        """Check if request to model_id is allowed."""
        with self._lock:
            circuit = self._get_circuit(model_id)
            return circuit.allow_request()

    def get_circuit_state(self, model_id: str) -> ModelCircuitState:
        """Retrieve current circuit state for a model."""
        with self._lock:
            circuit = self._get_circuit(model_id)
            # Trigger state update if cooldown elapsed
            circuit.allow_request()
            return circuit.state

    def record_success(self, model_id: str) -> None:
        """Record success on model_id."""
        with self._lock:
            circuit = self._get_circuit(model_id)
            circuit.record_success()

    def record_failure(self, model_id: str, is_transient: bool = True) -> None:
        """Record failure. Deterministic errors do not increment circuit breaker count."""
        if not is_transient:
            # Deterministic/schema errors should not trip circuit breaker
            return

        with self._lock:
            circuit = self._get_circuit(model_id)
            circuit.record_transient_failure()

    def record_transient_failure(self, model_id: str) -> None:
        """Convenience alias for recording transient gateway failures."""
        self.record_failure(model_id, is_transient=True)

    def get_state(self, model_id: str) -> ModelCircuitState:
        """Convenience alias for get_circuit_state."""
        return self.get_circuit_state(model_id)

    def reset(self, model_id: Optional[str] = None) -> None:
        """Reset single or all circuits."""
        with self._lock:
            if model_id:
                if model_id in self._circuits:
                    self._circuits[model_id].record_success()
            else:
                self._circuits.clear()


# Singleton instance
_breaker: Optional[ModelCircuitBreaker] = None
_breaker_lock = threading.Lock()


def get_circuit_breaker() -> ModelCircuitBreaker:
    global _breaker
    with _breaker_lock:
        if _breaker is None:
            _breaker = ModelCircuitBreaker()
        return _breaker
