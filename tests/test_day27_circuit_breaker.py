"""Day 27 Unit Tests: Enterprise 3-State Circuit Breaker.

Tests:
- Initial CLOSED state permits requests
- Consecutive failures trip circuit to OPEN
- OPEN state blocks requests immediately without network delay
- Monotonic cooldown expiration transitions to HALF_OPEN probe state
- Successful probes in HALF_OPEN recover circuit to CLOSED
- Failed probe in HALF_OPEN re-opens circuit
- Provider isolation: tripping Provider A never impacts Provider B
"""

import time
import unittest

from zye_ai_plugins.resilience import (
    STATE_CLOSED,
    STATE_HALF_OPEN,
    STATE_OPEN,
    CircuitBreakerRegistry,
    ProviderCircuitState,
)


class TestDay27CircuitBreaker(unittest.TestCase):
    """Test suite for 3-state circuit breaker."""

    def setUp(self):
        self.circuit = ProviderCircuitState(
            provider_id="test_unit_provider",
            failure_threshold=3,
            open_duration_seconds=0.2,  # Short cooldown for test speed
            recovery_threshold=2,
            half_open_probes=1,
        )

    def test_01_closed_state_permits_requests(self):
        """Verify new circuit breaker starts CLOSED and permits execution."""
        self.assertEqual(self.circuit.state, STATE_CLOSED)
        permitted, reason = self.circuit.check_permission()
        self.assertTrue(permitted)
        self.assertIn("CLOSED", reason)

    def test_02_trips_to_open_after_threshold(self):
        """Verify 3 consecutive failures transitions circuit to OPEN."""
        self.circuit.record_failure("error 1")
        self.assertEqual(self.circuit.state, STATE_CLOSED)
        self.circuit.record_failure("error 2")
        self.assertEqual(self.circuit.state, STATE_CLOSED)
        self.circuit.record_failure("error 3")
        self.assertEqual(self.circuit.state, STATE_OPEN)

        # OPEN state must block requests
        permitted, reason = self.circuit.check_permission()
        self.assertFalse(permitted)
        self.assertIn("OPEN", reason)

    def test_03_cooldown_to_half_open_and_recovery(self):
        """Verify cooldown transitions OPEN -> HALF_OPEN -> CLOSED on success."""
        # Trip to OPEN
        for i in range(3):
            self.circuit.record_failure(f"error {i}")
        self.assertEqual(self.circuit.state, STATE_OPEN)

        # Wait for monotonic cooldown (0.25s > 0.2s)
        time.sleep(0.25)

        # Next check should transition to HALF_OPEN
        permitted, reason = self.circuit.check_permission()
        self.assertTrue(permitted)
        self.assertEqual(self.circuit.state, STATE_HALF_OPEN)

        # First probe success
        self.circuit.record_success()
        self.assertEqual(self.circuit.state, STATE_HALF_OPEN)

        # Second probe success reaches recovery_threshold=2 -> CLOSED
        self.circuit.record_success()
        self.assertEqual(self.circuit.state, STATE_CLOSED)
        self.assertEqual(self.circuit.consecutive_failures, 0)

    def test_04_probe_failure_reopens_circuit(self):
        """Verify failed probe in HALF_OPEN immediately re-trips to OPEN."""
        for i in range(3):
            self.circuit.record_failure(f"error {i}")
        time.sleep(0.25)
        self.circuit.check_permission()
        self.assertEqual(self.circuit.state, STATE_HALF_OPEN)

        # Probe fails
        self.circuit.record_failure("probe failed")
        self.assertEqual(self.circuit.state, STATE_OPEN)

    def test_05_provider_isolation(self):
        """Verify tripping one provider leaves independent providers unaffected."""
        registry = CircuitBreakerRegistry()
        cb_chatgpt = registry.get_circuit("chatgpt_isolated")
        cb_claude = registry.get_circuit("claude_isolated")

        # Trip ChatGPT
        for _ in range(3):
            cb_chatgpt.record_failure("chatgpt error")

        self.assertEqual(cb_chatgpt.state, STATE_OPEN)
        self.assertEqual(cb_claude.state, STATE_CLOSED)

        # Claude is still permitted
        permitted, _ = cb_claude.check_permission()
        self.assertTrue(permitted)


if __name__ == "__main__":
    unittest.main()
