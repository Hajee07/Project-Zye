"""
Unit tests for Retry & Circuit Breaker Engine (Day 17).
Verifies bounded exponential backoff, circuit breaker state machine,
timeout execution bounds, and idempotency classification.
"""

from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock

from zye_reliability.error_handler import CircuitOpenError, ZyeTimeoutError
from zye_reliability.retry_manager import (
    CircuitBreaker,
    CircuitState,
    RetryPolicy,
    calculate_backoff,
    execute_with_retry,
    execute_with_timeout,
    is_idempotent_operation,
)


class TestDay17RetryManager(unittest.TestCase):

    def test_idempotency_classification(self) -> None:
        """Verify non-idempotent operations are correctly blocked from auto-replay."""
        # Non-idempotent
        self.assertFalse(is_idempotent_operation("terminate_process"))
        self.assertFalse(is_idempotent_operation("empty_recycle_bin"))
        self.assertFalse(is_idempotent_operation("power_action"))
        self.assertFalse(is_idempotent_operation("send_whatsapp_message"))
        self.assertFalse(is_idempotent_operation("patch_own_code"))

        # Idempotent / Read-only
        self.assertTrue(is_idempotent_operation("list_running_processes"))
        self.assertTrue(is_idempotent_operation("get_process_details"))
        self.assertTrue(is_idempotent_operation("check_process_responsiveness"))
        self.assertTrue(is_idempotent_operation("preview_recycle_bin"))
        self.assertTrue(is_idempotent_operation("read_own_source_code"))

    def test_circuit_breaker_transitions(self) -> None:
        """Verify CLOSED -> OPEN -> HALF_OPEN -> CLOSED state transitions."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.2)
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.can_execute())

        # First failure keeps it CLOSED (threshold is 2)
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.CLOSED)

        # Second failure trips it OPEN
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.can_execute())

        # Wait for recovery timeout
        time.sleep(0.25)
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
        self.assertTrue(cb.can_execute())

        # Successes in HALF_OPEN close the circuit
        cb.record_success()
        cb.record_success()
        self.assertEqual(cb.state, CircuitState.CLOSED)

    def test_calculate_backoff(self) -> None:
        """Verify exponential backoff calculation remains bounded."""
        policy = RetryPolicy(base_delay=0.1, max_delay=1.0, backoff_factor=2.0, jitter=False)
        d0 = calculate_backoff(0, policy)
        self.assertEqual(d0, 0.1)

        d1 = calculate_backoff(1, policy)
        self.assertEqual(d1, 0.2)

        d5 = calculate_backoff(5, policy)
        self.assertEqual(d5, 1.0)  # Capped at max_delay

    def test_execute_with_retry_success(self) -> None:
        """Verify execute_with_retry succeeds after transient failures."""
        calls = 0

        def flaky() -> str:
            nonlocal calls
            calls += 1
            if calls < 2:
                raise ConnectionError("Transient drop")
            return "SUCCESS"

        policy = RetryPolicy(max_retries=3, base_delay=0.01, jitter=False)
        res = execute_with_retry(flaky, policy=policy)
        self.assertEqual(res, "SUCCESS")
        self.assertEqual(calls, 2)

    def test_execute_with_retry_exhausted(self) -> None:
        """Verify execute_with_retry raises after retries exhausted."""
        def always_fail() -> None:
            raise ConnectionError("Permanent failure")

        policy = RetryPolicy(max_retries=2, base_delay=0.01, jitter=False)
        with self.assertRaises(ConnectionError):
            execute_with_retry(always_fail, policy=policy)

    def test_execute_with_timeout_success(self) -> None:
        """Verify execute_with_timeout returns result when callable finishes quickly."""
        def quick() -> int:
            return 42

        res = execute_with_timeout(quick, timeout_seconds=1.0)
        self.assertEqual(res, 42)

    def test_execute_with_timeout_exceeded(self) -> None:
        """Verify execute_with_timeout raises ZyeTimeoutError when execution hangs."""
        def slow() -> None:
            time.sleep(0.5)

        with self.assertRaises(ZyeTimeoutError):
            execute_with_timeout(slow, timeout_seconds=0.1)


if __name__ == "__main__":
    unittest.main()
