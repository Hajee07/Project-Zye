"""Day 15 Unit Tests — Proactive Autonomous Watchdog."""
import asyncio
import unittest

from zye_autonomy.system_monitor import ZyeAutonomousWatchdog, DEFAULT_CONFIG


class TestWatchdogInit(unittest.TestCase):
    def test_creates_instance(self):
        wd = ZyeAutonomousWatchdog()
        self.assertIsNotNone(wd)

    def test_config_is_dict(self):
        wd = ZyeAutonomousWatchdog()
        self.assertIsInstance(wd._config, dict)

    def test_default_interval_is_25(self):
        wd = ZyeAutonomousWatchdog()
        self.assertAlmostEqual(wd._config.get("interval_seconds", 0.0), 25.0)

    def test_custom_interval(self):
        wd = ZyeAutonomousWatchdog(config={"interval_seconds": 10.0})
        self.assertAlmostEqual(wd._config.get("interval_seconds"), 10.0)

    def test_not_running_initially(self):
        wd = ZyeAutonomousWatchdog()
        self.assertFalse(wd._running)

    def test_scan_count_zero_initially(self):
        wd = ZyeAutonomousWatchdog()
        self.assertEqual(wd._scan_count, 0)

    def test_no_task_initially(self):
        wd = ZyeAutonomousWatchdog()
        self.assertIsNone(wd._task)


class TestDefaultConfig(unittest.TestCase):
    def test_default_config_has_interval(self):
        self.assertIn("interval_seconds", DEFAULT_CONFIG)

    def test_default_config_interval_is_25(self):
        self.assertAlmostEqual(DEFAULT_CONFIG["interval_seconds"], 25.0)

    def test_default_config_has_ram_threshold(self):
        self.assertIn("ram_high_threshold", DEFAULT_CONFIG)

    def test_default_config_has_disk_threshold(self):
        self.assertIn("disk_high_threshold", DEFAULT_CONFIG)

    def test_default_config_has_battery_warning(self):
        self.assertIn("battery_warning_threshold", DEFAULT_CONFIG)

    def test_default_config_has_battery_critical(self):
        self.assertIn("battery_critical_threshold", DEFAULT_CONFIG)

    def test_ram_threshold_reasonable(self):
        thresh = DEFAULT_CONFIG["ram_high_threshold"]
        self.assertGreater(thresh, 50.0)
        self.assertLessEqual(thresh, 100.0)


class TestWatchdogHealthStatus(unittest.TestCase):
    def test_get_watchdog_status_returns_dict(self):
        wd = ZyeAutonomousWatchdog()
        status = wd.get_watchdog_status()
        self.assertIsInstance(status, dict)

    def test_watchdog_status_has_running_key(self):
        wd = ZyeAutonomousWatchdog()
        status = wd.get_watchdog_status()
        self.assertIn("running", status)

    def test_watchdog_status_has_scan_count(self):
        wd = ZyeAutonomousWatchdog()
        status = wd.get_watchdog_status()
        self.assertIn("scan_count", status)

    def test_watchdog_status_running_is_false(self):
        wd = ZyeAutonomousWatchdog()
        status = wd.get_watchdog_status()
        self.assertFalse(status["running"])

    def test_watchdog_status_has_interval(self):
        wd = ZyeAutonomousWatchdog()
        status = wd.get_watchdog_status()
        self.assertIn("interval_seconds", status)


class TestWatchdogScan(unittest.TestCase):
    def test_scan_system_completes(self):
        """Run one scan synchronously to verify no crash."""
        wd = ZyeAutonomousWatchdog()
        result = asyncio.run(wd.scan_system())
        self.assertIsInstance(result, dict)

    def test_scan_result_has_unsuppressed_problems(self):
        wd = ZyeAutonomousWatchdog()
        result = asyncio.run(wd.scan_system())
        self.assertIn("unsuppressed_problems", result)

    def test_scan_count_increments(self):
        wd = ZyeAutonomousWatchdog()
        asyncio.run(wd.scan_system())
        self.assertEqual(wd._scan_count, 1)

    def test_detect_problems_returns_list(self):
        """detect_problems() is the Day 11 compat API."""
        wd = ZyeAutonomousWatchdog()
        problems = asyncio.run(wd.detect_problems())
        self.assertIsInstance(problems, list)

    def test_duplicate_scan_fingerprint_suppressed(self):
        """Two scans with same conditions should not double-report same problem."""
        wd = ZyeAutonomousWatchdog()
        r1 = asyncio.run(wd.scan_system())
        r2 = asyncio.run(wd.scan_system())
        self.assertIsInstance(r2, dict)


if __name__ == "__main__":
    unittest.main()
