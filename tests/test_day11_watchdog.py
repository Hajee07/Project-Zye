"""Unit tests for Zye Day 11 Autonomous Problem Identification & Watchdog."""

import asyncio
import os
import pathlib
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from zye_autonomy.watchdog import ZyeAutonomousWatchdog


class TestZyeAutonomousWatchdog(unittest.TestCase):
    def setUp(self):
        self.config = {
            "ram_warning_pct": 88.0,
            "disk_warning_pct": 92.0,
            "battery_warning_pct": 15.0,
            "battery_critical_pct": 8.0,
            "alert_cooldown_seconds": 1.0,  # Fast cooldown for testing
            "interval_seconds": 0.05,
        }
        self.wd = ZyeAutonomousWatchdog(config=self.config)

    def test_01_normal_system(self):
        mock_vm = MagicMock(percent=45.0, available=8 * (1024**3))
        mock_disk = MagicMock(percent=50.0, free=100 * (1024**3))
        mock_batt = MagicMock(percent=85.0, power_plugged=True)

        with patch("psutil.virtual_memory", return_value=mock_vm), \
             patch("psutil.disk_usage", return_value=mock_disk), \
             patch("psutil.sensors_battery", return_value=mock_batt), \
             patch("pathlib.Path.exists", return_value=False):

            async def _run():
                probs = await self.wd.detect_problems()
                self.assertEqual(len(probs), 0)
            asyncio.run(_run())

    def test_02_high_ram(self):
        mock_vm = MagicMock(percent=91.0, available=1 * (1024**3))
        with patch("psutil.virtual_memory", return_value=mock_vm), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
             patch("psutil.sensors_battery", return_value=None), \
             patch("pathlib.Path.exists", return_value=False):

            async def _run():
                probs = await self.wd.detect_problems()
                ram_probs = [p for p in probs if p["category"] == "RAM"]
                self.assertEqual(len(ram_probs), 1)
                self.assertEqual(ram_probs[0]["severity"], "HIGH")
                self.assertIn("91.0%", ram_probs[0]["description"])
            asyncio.run(_run())

    def test_03_high_disk_usage(self):
        mock_vm = MagicMock(percent=40.0)
        mock_disk = MagicMock(percent=95.0, free=5 * (1024**3))
        with patch("psutil.virtual_memory", return_value=mock_vm), \
             patch("psutil.disk_usage", return_value=mock_disk), \
             patch("psutil.sensors_battery", return_value=None), \
             patch("pathlib.Path.exists", return_value=False):

            async def _run():
                probs = await self.wd.detect_problems()
                disk_probs = [p for p in probs if p["category"] == "DISK"]
                self.assertEqual(len(disk_probs), 1)
                self.assertEqual(disk_probs[0]["severity"], "MEDIUM")
            asyncio.run(_run())

    def test_04_low_battery(self):
        mock_batt = MagicMock(percent=12.0, power_plugged=False)
        with patch("psutil.virtual_memory", return_value=MagicMock(percent=40.0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
             patch("psutil.sensors_battery", return_value=mock_batt), \
             patch("pathlib.Path.exists", return_value=False):

            async def _run():
                probs = await self.wd.detect_problems()
                batt_probs = [p for p in probs if p["category"] == "BATTERY"]
                self.assertEqual(len(batt_probs), 1)
                self.assertEqual(batt_probs[0]["severity"], "HIGH")
            asyncio.run(_run())

    def test_05_critical_battery(self):
        mock_batt = MagicMock(percent=6.0, power_plugged=False)
        with patch("psutil.virtual_memory", return_value=MagicMock(percent=40.0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
             patch("psutil.sensors_battery", return_value=mock_batt), \
             patch("pathlib.Path.exists", return_value=False):

            async def _run():
                probs = await self.wd.detect_problems()
                batt_probs = [p for p in probs if p["category"] == "BATTERY"]
                self.assertEqual(len(batt_probs), 1)
                self.assertEqual(batt_probs[0]["severity"], "CRITICAL")
            asyncio.run(_run())

    def test_06_missing_battery_sensor(self):
        with patch("psutil.virtual_memory", return_value=MagicMock(percent=40.0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
             patch("psutil.sensors_battery", return_value=None), \
             patch("pathlib.Path.exists", return_value=False):

            async def _run():
                probs = await self.wd.detect_problems()
                batt_probs = [p for p in probs if p["category"] == "BATTERY"]
                self.assertEqual(len(batt_probs), 0)
            asyncio.run(_run())

    def test_07_recent_bug_report(self):
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as tmp:
            tmp.write("Normal log\n2026-11-19 BUG REPORT: NullPointerException in module\nAnother line\n")
            tmp_path = tmp.name

        try:
            with patch("pathlib.Path.exists", return_value=True), \
                 patch("pathlib.Path.read_text", return_value="BUG REPORT: crash in worker\n"), \
                 patch("psutil.virtual_memory", return_value=MagicMock(percent=40.0)), \
                 patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
                 patch("psutil.sensors_battery", return_value=None):

                async def _run():
                    probs = await self.wd.detect_problems()
                    err_probs = [p for p in probs if p["category"] == "ERROR_LOG"]
                    self.assertEqual(len(err_probs), 1)
                    self.assertEqual(err_probs[0]["severity"], "MEDIUM")
                asyncio.run(_run())
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_08_no_error_log(self):
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=40.0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
             patch("psutil.sensors_battery", return_value=None):

            async def _run():
                probs = await self.wd.detect_problems()
                err_probs = [p for p in probs if p["category"] == "ERROR_LOG"]
                self.assertEqual(len(err_probs), 0)
            asyncio.run(_run())

    def test_09_alert_deduplication(self):
        mock_vm = MagicMock(percent=95.0, available=1)
        with patch("psutil.virtual_memory", return_value=mock_vm), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
             patch("psutil.sensors_battery", return_value=None), \
             patch("pathlib.Path.exists", return_value=False):

            async def _run():
                first = await self.wd.scan_system()
                self.assertEqual(len(first), 1)

                # Second scan immediately: should be filtered out by cooldown
                second = await self.wd.scan_system()
                self.assertEqual(len(second), 0)
            asyncio.run(_run())

    def test_10_alert_cooldown_expiration(self):
        # Set short cooldown of 0.05s
        wd = ZyeAutonomousWatchdog(config={"alert_cooldown_seconds": 0.05, "ram_warning_pct": 80.0})
        mock_vm = MagicMock(percent=95.0, available=1)

        with patch("psutil.virtual_memory", return_value=mock_vm), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
             patch("psutil.sensors_battery", return_value=None), \
             patch("pathlib.Path.exists", return_value=False):

            async def _run():
                first = await wd.scan_system()
                self.assertEqual(len(first), 1)

                await asyncio.sleep(0.06)

                # After cooldown expired, should re-alert
                second = await wd.scan_system()
                self.assertEqual(len(second), 1)
            asyncio.run(_run())

    def test_11_problem_recovery_detection(self):
        mock_high = MagicMock(percent=95.0, available=1)
        mock_normal = MagicMock(percent=40.0, available=8 * (1024**3))

        with patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
             patch("psutil.sensors_battery", return_value=None), \
             patch("pathlib.Path.exists", return_value=False):

            async def _run():
                with patch("psutil.virtual_memory", return_value=mock_high):
                    await self.wd.scan_system()
                    self.assertEqual(len(self.wd._active_problem_fingerprints), 1)

                with patch("psutil.virtual_memory", return_value=mock_normal):
                    await self.wd.scan_system()
                    # Problem cleared
                    self.assertEqual(len(self.wd._active_problem_fingerprints), 0)
                    self.assertGreaterEqual(len(self.wd._resolved_problems), 1)
            asyncio.run(_run())

    def test_12_watchdog_lifecycle_start_and_stop(self):
        async def _run():
            await self.wd.start()
            self.assertTrue(self.wd._running)
            status = self.wd.get_watchdog_status()
            self.assertTrue(status["running"])
            await self.wd.stop()
            self.assertFalse(self.wd._running)
        asyncio.run(_run())

    def test_13_duplicate_watchdog_start_prevention(self):
        async def _run():
            await self.wd.start()
            # Attempt second start
            await self.wd.start()
            self.assertTrue(self.wd._running)
            await self.wd.stop()
        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
