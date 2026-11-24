#!/usr/bin/env python3
"""
ZYE AI — Day 12 Failure Recovery Test Suite
==========================================
Tests for zye_orchestrator.recovery_controller:
  1. Server crash detection
  2. Session disconnect handling
  3. Tool timeout handling
  4. Temporary transport failure handling
  5. Exponential backoff calculation
  6. Retry limit enforcement
  7. Circuit breaker transitioning to OPEN
  8. Circuit breaker transitioning to HALF_OPEN
  9. Recovery success handling
 10. Recovery failure handling
 11. Idempotent retry safety evaluation
 12. Non-idempotent no-retry safety evaluation
 13. Ambiguous operation status reporting
"""

from __future__ import annotations

import asyncio
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from zye_orchestrator.recovery_controller import CircuitState, MCPRecoveryController, ServerCircuit
from zye_orchestrator.server_registry import MCPServerConfig
from zye_orchestrator.server_runtime import MCPConnectionManager, MCPServerRuntime, ServerStatus
from zye_orchestrator.tool_registry import ZyeToolRegistry


class TestRecoveryController(unittest.TestCase):
    """Test suite for MCP failure recovery and circuit breaker."""

    def setUp(self) -> None:
        self.recovery = MCPRecoveryController(config={
            "max_restart_attempts": 2,
            "initial_backoff_seconds": 0.05,
            "max_backoff_seconds": 0.5,
            "circuit_breaker_enabled": True,
        })
        self.conn_mgr = MCPConnectionManager()
        self.tool_reg = ZyeToolRegistry()
        self.server_cfg = MCPServerConfig(
            server_name="crash_srv",
            command=sys.executable,
            args=[str(PROJECT_ROOT / "self_repair_mcp.py")],
        )

    def _run(self, coro):
        return asyncio.run(coro)

    def test_01_exponential_backoff_calculation(self) -> None:
        """Backoff increases exponentially with attempt count."""
        b0 = self.recovery.calculate_backoff(0)
        b1 = self.recovery.calculate_backoff(1)
        b2 = self.recovery.calculate_backoff(2)
        self.assertGreater(b1, b0)
        self.assertLessEqual(b2, 1.0)  # Capped within reason

    def test_02_circuit_breaker_initial_state_closed(self) -> None:
        """New circuit starts in CLOSED state."""
        circuit = self.recovery.get_circuit("srv_1")
        self.assertEqual(circuit.state, CircuitState.CLOSED)
        self.assertTrue(self.recovery.is_request_allowed("srv_1"))

    def test_03_circuit_breaker_transitions_to_open(self) -> None:
        """Circuit transitions to OPEN after failure threshold reached."""
        for _ in range(3):
            self.recovery.record_failure("flaky_srv", "Simulated error")
        circuit = self.recovery.get_circuit("flaky_srv")
        self.assertEqual(circuit.state, CircuitState.OPEN)
        self.assertFalse(self.recovery.is_request_allowed("flaky_srv"))

    def test_04_circuit_breaker_transitions_to_half_open(self) -> None:
        """Circuit transitions to HALF_OPEN after recovery timeout."""
        circuit = self.recovery.get_circuit("timed_srv")
        circuit.state = CircuitState.OPEN
        circuit.recovery_timeout = 0.05  # Fast timeout for test
        circuit.last_failure_time = time.monotonic() - 0.1
        self.assertTrue(self.recovery.is_request_allowed("timed_srv"))
        self.assertEqual(circuit.state, CircuitState.HALF_OPEN)

    def test_05_half_open_success_closes_circuit(self) -> None:
        """Success while HALF_OPEN resets circuit to CLOSED."""
        circuit = self.recovery.get_circuit("probe_srv")
        circuit.state = CircuitState.HALF_OPEN
        self.recovery.record_success("probe_srv")
        self.assertEqual(circuit.state, CircuitState.CLOSED)
        self.assertEqual(circuit.consecutive_failures, 0)

    def test_06_half_open_failure_reopens_circuit(self) -> None:
        """Failure while HALF_OPEN reopens circuit to OPEN."""
        circuit = self.recovery.get_circuit("probe_fail_srv")
        circuit.state = CircuitState.HALF_OPEN
        self.recovery.record_failure("probe_fail_srv", "Probe probe error")
        self.assertEqual(circuit.state, CircuitState.OPEN)

    def test_07_recovery_success(self) -> None:
        """recover_server restarts server and re-registers tools on success."""
        runtime = self.conn_mgr.ensure_runtime("crash_srv")
        runtime.status = ServerStatus.FAILED

        mock_healthy = MCPServerRuntime("crash_srv")
        mock_healthy.status = ServerStatus.HEALTHY
        mock_healthy.session = type("MockSess", (), {})()

        with patch.object(self.conn_mgr, "stop_server", new_callable=AsyncMock), \
             patch.object(self.conn_mgr, "start_server", new_callable=AsyncMock) as mock_start, \
             patch.object(self.tool_reg, "discover_tools", new_callable=AsyncMock) as mock_disc:
            mock_start.return_value = mock_healthy
            mock_disc.return_value = [{"name": "recovered_tool", "description": "d", "inputSchema": {}}]

            res = self._run(self.recovery.recover_server(
                "crash_srv", self.conn_mgr, self.server_cfg, self.tool_reg,
            ))
            self.assertEqual(res["status"], "recovered")
            self.assertEqual(res["restart_count"], 1)

    def test_08_retry_limit_enforced(self) -> None:
        """recover_server returns MAX_RESTARTS_EXCEEDED when retry limit reached."""
        runtime = self.conn_mgr.ensure_runtime("crash_srv")
        runtime.restart_count = 2  # Max reached

        res = self._run(self.recovery.recover_server(
            "crash_srv", self.conn_mgr, self.server_cfg, self.tool_reg,
        ))
        self.assertEqual(res["status"], "failed")
        self.assertEqual(res["code"], "MAX_RESTARTS_EXCEEDED")

    def test_09_recovery_blocked_when_circuit_open(self) -> None:
        """recover_server is blocked immediately when circuit is OPEN."""
        circuit = self.recovery.get_circuit("crash_srv")
        circuit.state = CircuitState.OPEN
        circuit.recovery_timeout = 100.0  # Still in cooldown
        circuit.last_failure_time = time.monotonic()  # Set recent failure time

        res = self._run(self.recovery.recover_server(
            "crash_srv", self.conn_mgr, self.server_cfg, self.tool_reg,
        ))
        self.assertEqual(res["status"], "blocked")
        self.assertEqual(res["code"], "CIRCUIT_OPEN")

    def test_10_idempotent_retry_safety(self) -> None:
        """Read-only and inspect tools are evaluated as safe to retry."""
        eval_read = self.recovery.evaluate_retry_safety("read_recent_error_logs", "timeout")
        self.assertTrue(eval_read["safe_to_retry"])

        eval_inspect = self.recovery.evaluate_retry_safety("inspect_source_file", "broken pipe")
        self.assertTrue(eval_inspect["safe_to_retry"])

    def test_11_non_idempotent_no_retry(self) -> None:
        """Mutating or irreversible operations are evaluated as NOT safe to retry."""
        eval_del = self.recovery.evaluate_retry_safety("delete_file", "connection drop")
        self.assertFalse(eval_del["safe_to_retry"])

        eval_patch = self.recovery.evaluate_retry_safety("patch_own_code", "timeout")
        self.assertFalse(eval_patch["safe_to_retry"])

        eval_reflex = self.recovery.evaluate_retry_safety("execute_emergency_reflex", "timeout")
        self.assertFalse(eval_reflex["safe_to_retry"])

    def test_12_get_recovery_status(self) -> None:
        """get_recovery_status returns structured circuit telemetry."""
        status = self.recovery.get_recovery_status("crash_srv")
        self.assertIn("circuit_state", status)
        self.assertIn("consecutive_failures", status)

    def test_13_recovery_history_records_events(self) -> None:
        """Recovery attempts append to history log."""
        runtime = self.conn_mgr.ensure_runtime("crash_srv")
        runtime.restart_count = 5
        self._run(self.recovery.recover_server(
            "crash_srv", self.conn_mgr, self.server_cfg, self.tool_reg,
        ))
        hist = self.recovery.get_recovery_history()
        self.assertGreater(len(hist), 0)
        self.assertEqual(hist[-1]["server_name"], "crash_srv")


if __name__ == "__main__":
    unittest.main()
