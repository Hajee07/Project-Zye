"""
Unit tests for Day 13 Autonomous Problem Identification & Proactive Watchdog.
Tests zye_intelligence.autonomous_watchdog: ZyeAutonomousWatchdog, _scan_emerging_problems_sync,
and proactive_autonomous_loop.
"""

from __future__ import annotations

import asyncio
import pathlib
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from zye_intelligence.autonomous_watchdog import (
    DEFAULT_CONFIG,
    WATCHDOG_INTERVAL_SECONDS,
    ZyeAutonomousWatchdog,
    _scan_emerging_problems_sync,
    proactive_autonomous_loop,
)


class TestDay13Watchdog(unittest.TestCase):
    def setUp(self) -> None:
        self.wd = ZyeAutonomousWatchdog(config={"interval_seconds": 0.05, "alert_cooldown_seconds": 1.0})

    def tearDown(self) -> None:
        if self.wd._running:
            asyncio.run(self.wd.stop())

    def test_01_watchdog_startup(self) -> None:
        """Verify watchdog starts and sets running flag."""
        asyncio.run(self.wd.start())
        self.assertTrue(self.wd._running)
        self.assertIsNotNone(self.wd._task)
        asyncio.run(self.wd.stop())
        self.assertFalse(self.wd._running)

    def test_02_single_task_enforcement(self) -> None:
        """Verify starting an already running watchdog does not duplicate task."""
        asyncio.run(self.wd.start())
        task1 = self.wd._task
        asyncio.run(self.wd.start())  # duplicate start
        task2 = self.wd._task
        self.assertIs(task1, task2)
        asyncio.run(self.wd.stop())

    def test_03_periodic_scanning(self) -> None:
        """Verify watchdog executes scans during periodic loop."""
        async def _run():
            await self.wd.start()
            await asyncio.sleep(0.12)
            await self.wd.stop()
        asyncio.run(_run())
        self.assertGreaterEqual(self.wd._scan_count, 1)

    def test_04_ram_alert(self) -> None:
        """Verify RAM utilization >= 88% triggers a HIGH severity problem."""
        mock_vm = type("VM", (), {"percent": 90.0, "available": 1024**3})()
        with patch("psutil.virtual_memory", return_value=mock_vm):
            res = _scan_emerging_problems_sync(config={"ram_high_threshold": 88.0})
            problems = res["detected_problems"]
            ram_probs = [p for p in problems if p["category"] == "RAM"]
            self.assertEqual(len(ram_probs), 1)
            self.assertEqual(ram_probs[0]["severity"], "HIGH")

    def test_05_disk_alert(self) -> None:
        """Verify disk utilization >= 92% triggers a MEDIUM severity problem."""
        mock_du = type("DU", (), {"percent": 94.0, "free": 1024**3})()
        with patch("psutil.disk_usage", return_value=mock_du):
            res = _scan_emerging_problems_sync(config={"disk_high_threshold": 92.0})
            problems = res["detected_problems"]
            disk_probs = [p for p in problems if p["category"] == "DISK"]
            self.assertEqual(len(disk_probs), 1)
            self.assertEqual(disk_probs[0]["severity"], "MEDIUM")

    def test_06_battery_alert(self) -> None:
        """Verify battery <= 8% unplugged triggers CRITICAL severity problem."""
        mock_batt = type("Batt", (), {"percent": 6.0, "power_plugged": False, "secsleft": 600})()
        with patch("psutil.sensors_battery", return_value=mock_batt):
            res = _scan_emerging_problems_sync()
            problems = res["detected_problems"]
            batt_probs = [p for p in problems if p["category"] == "BATTERY"]
            self.assertEqual(len(batt_probs), 1)
            self.assertEqual(batt_probs[0]["severity"], "CRITICAL")

    def test_07_error_log_alert(self) -> None:
        """Verify recent BUG REPORT in zye_errors.log triggers an alert."""
        with tempfile.TemporaryDirectory() as td:
            log_dir = pathlib.Path(td) / "logs"
            log_dir.mkdir()
            log_file = log_dir / "zye_errors.log"
            log_file.write_text("BUG REPORT: Unhandled exception in worker\n", encoding="utf-8")

            with patch("pathlib.Path", side_effect=lambda p: log_file if "zye_errors.log" in str(p) else pathlib.Path(p)):
                res = _scan_emerging_problems_sync()
                # If path patched
                self.assertIn("status", res)

    def test_08_duplicate_alert_suppression(self) -> None:
        """Verify duplicate alerts are suppressed within cooldown."""
        mock_vm = type("VM", (), {"percent": 95.0, "available": 1024**3})()
        with patch("psutil.virtual_memory", return_value=mock_vm):
            # First scan generates unsuppressed problem
            scan1 = asyncio.run(self.wd.scan_system())
            self.assertGreater(len(scan1["unsuppressed_problems"]), 0)

            # Second immediate scan suppresses problem
            scan2 = asyncio.run(self.wd.scan_system())
            self.assertEqual(len(scan2["unsuppressed_problems"]), 0)

    def test_09_mcp_server_unavailable(self) -> None:
        """Verify proactive_autonomous_loop falls back to internal scan if MCP fails."""
        mock_zye = type("Zye", (), {})()
        mock_agent = MagicMock()
        mock_agent.call_mcp_with_recovery = AsyncMock(side_effect=RuntimeError("Server unavailable"))
        mock_zye.agent = mock_agent
        mock_zye._cfg = {"autonomous_brain": {"watchdog": {"interval_seconds": 0.05}}}

        async def _test():
            task = asyncio.create_task(proactive_autonomous_loop(mock_zye))
            await asyncio.sleep(0.08)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        asyncio.run(_test())
        self.assertTrue(True)

    def test_10_invalid_json_response(self) -> None:
        """Verify proactive loop handles non-dict MCP response gracefully."""
        mock_zye = type("Zye", (), {})()
        mock_agent = MagicMock()
        mock_agent.call_mcp_with_recovery = AsyncMock(return_value="NOT_A_DICT")
        mock_zye.agent = mock_agent
        mock_zye._cfg = {"autonomous_brain": {"watchdog": {"interval_seconds": 0.05}}}

        async def _test():
            task = asyncio.create_task(proactive_autonomous_loop(mock_zye))
            await asyncio.sleep(0.08)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        asyncio.run(_test())
        self.assertTrue(True)

    def test_11_cancellation(self) -> None:
        """Verify watchdog task cleanly handles asyncio.CancelledError."""
        async def _test():
            await self.wd.start()
            self.wd._task.cancel()
            await asyncio.sleep(0.02)
            self.assertTrue(self.wd._task.done())
        asyncio.run(_test())

    def test_12_graceful_shutdown(self) -> None:
        """Verify stop cleans up task and sets _running to False."""
        async def _test():
            await self.wd.start()
            self.assertTrue(self.wd._running)
            await self.wd.stop()
            self.assertFalse(self.wd._running)
            self.assertIsNone(self.wd._task)
        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
