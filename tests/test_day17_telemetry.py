"""
Unit tests for Telemetry, Audit & Metrics Engine (Day 17).
Verifies rotating file logger creation, secret scrubbing, error distribution aggregation,
tool latency statistics, and correlation context propagation.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zye_reliability.telemetry import CorrelationContext, ZyeTelemetryLogger


class TestDay17Telemetry(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_path = Path(self.temp_dir.name) / "test_telemetry.log"
        self.tel = ZyeTelemetryLogger(log_path=self.log_path)

    def tearDown(self) -> None:
        if hasattr(self, "tel"):
            self.tel.close()
        self.temp_dir.cleanup()

    def test_correlation_context(self) -> None:
        """Verify correlation context trace ID propagation."""
        tid = CorrelationContext.get_trace_id()
        self.assertTrue(len(tid) >= 8)

        CorrelationContext.set_trace_id("custom_trace_123")
        self.assertEqual(CorrelationContext.get_trace_id(), "custom_trace_123")

    def test_log_tool_execution_and_health(self) -> None:
        """Verify logging tool executions updates tool health metrics."""
        self.tel.log_tool_execution(
            tool_name="control_volume",
            trace_id="tid_001",
            duration_ms=45.2,
            status="SUCCESS",
        )
        self.tel.log_tool_execution(
            tool_name="control_volume",
            trace_id="tid_002",
            duration_ms=55.0,
            status="SUCCESS",
        )
        self.tel.log_tool_execution(
            tool_name="control_volume",
            trace_id="tid_003",
            duration_ms=60.0,
            status="ERROR",
        )

        health = self.tel.get_tool_health("control_volume", last_n_minutes=60)
        self.assertEqual(health["total_calls"], 3)
        self.assertEqual(health["success_calls"], 2)
        self.assertEqual(health["failed_calls"], 1)
        self.assertAlmostEqual(health["success_rate"], 0.6667, places=3)
        self.assertEqual(health["status"], "DEGRADED")

    def test_log_error_and_summary_with_redaction(self) -> None:
        """Verify error logging, secret scrubbing, and summary aggregation."""
        self.tel.log_error(
            tool_name="test_tool",
            trace_id="tid_101",
            error_code="PROCESS_NOT_FOUND",
            message="Vanished with secret key AIzaSyA1234567890123456789012345678901",
        )
        self.tel.log_error(
            tool_name="test_tool",
            trace_id="tid_102",
            error_code="PROCESS_NOT_FOUND",
            message="Second process vanished",
        )
        self.tel.log_error(
            tool_name="other_tool",
            trace_id="tid_103",
            error_code="ACCESS_DENIED",
            message="No rights",
        )

        summary = self.tel.get_error_summary(last_n_minutes=60)
        self.assertEqual(summary["total_errors"], 3)
        self.assertEqual(summary["by_error_code"].get("PROCESS_NOT_FOUND"), 2)
        self.assertEqual(summary["by_error_code"].get("ACCESS_DENIED"), 1)

        # Check log file on disk does not contain raw API key
        raw_log = self.log_path.read_text(encoding="utf-8")
        self.assertNotIn("AIzaSy", raw_log)
        self.assertIn("[REDACTED_GEMINI_KEY]", raw_log)

    def test_log_recovery_and_server_health(self) -> None:
        """Verify recovery event logging and server health categorization."""
        self.tel.log_recovery("windows_control", "rec_01", "hot_reload", "SUCCESS")
        self.tel.log_recovery("windows_control", "rec_02", "restart", "SUCCESS")

        h = self.tel.get_server_health("windows_control", last_n_minutes=60)
        self.assertEqual(h["total_recoveries"], 2)
        self.assertEqual(h["successful_recoveries"], 2)
        self.assertEqual(h["health_status"], "HEALTHY")


if __name__ == "__main__":
    unittest.main()
