"""Day 15 Unit Tests — Live System Preflight Telemetry Engine."""
import pathlib
import unittest

from zye_autonomy.system_preflight import ZyeSystemPreflight


class TestSystemPreflightInit(unittest.TestCase):
    def test_creates_instance(self):
        pf = ZyeSystemPreflight()
        self.assertIsNotNone(pf)

    def test_custom_config(self):
        pf = ZyeSystemPreflight(config={"ram_high": 90.0})
        self.assertEqual(pf._config.get("ram_high"), 90.0)


class TestPreflightMemoryInspection(unittest.TestCase):
    def setUp(self):
        self.pf = ZyeSystemPreflight()

    def test_inspect_memory_returns_dict(self):
        mem = self.pf.inspect_memory()
        self.assertIsInstance(mem, dict)

    def test_inspect_memory_has_percent(self):
        mem = self.pf.inspect_memory()
        self.assertIn("percent", mem)

    def test_memory_percent_range(self):
        mem = self.pf.inspect_memory()
        pct = mem.get("percent", 0.0)
        if isinstance(pct, (int, float)):
            self.assertGreaterEqual(pct, 0.0)
            self.assertLessEqual(pct, 100.0)


class TestPreflightCPUInspection(unittest.TestCase):
    def setUp(self):
        self.pf = ZyeSystemPreflight()

    def test_inspect_cpu_returns_dict(self):
        cpu = self.pf.inspect_cpu(interval=0.01)
        self.assertIsInstance(cpu, dict)

    def test_inspect_cpu_has_percent(self):
        cpu = self.pf.inspect_cpu(interval=0.01)
        self.assertIn("percent", cpu)


class TestPreflightStorageInspection(unittest.TestCase):
    def setUp(self):
        self.pf = ZyeSystemPreflight()

    def test_inspect_storage_returns_dict(self):
        disk = self.pf.inspect_storage()
        self.assertIsInstance(disk, dict)

    def test_inspect_storage_has_percent(self):
        disk = self.pf.inspect_storage()
        self.assertIn("percent", disk)


class TestPreflightBattery(unittest.TestCase):
    def setUp(self):
        self.pf = ZyeSystemPreflight()

    def test_inspect_battery_returns_dict(self):
        batt = self.pf.inspect_battery()
        self.assertIsInstance(batt, dict)

    def test_battery_no_crash_without_hardware(self):
        # Should not raise even if no battery present
        try:
            self.pf.inspect_battery()
        except Exception as e:
            self.fail(f"inspect_battery() raised unexpectedly: {e}")


class TestPreflightTargetPaths(unittest.TestCase):
    def setUp(self):
        self.pf = ZyeSystemPreflight()

    def test_inspect_existing_path(self):
        result = self.pf.inspect_target_paths(["d:/Zye/main.py"])
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_inspect_nonexistent_path_no_crash(self):
        try:
            result = self.pf.inspect_target_paths(["d:/Zye/does_not_exist_xyz.py"])
            self.assertIsInstance(result, list)
        except Exception as e:
            self.fail(f"Non-existent path should not raise: {e}")

    def test_inspect_empty_list_no_crash(self):
        result = self.pf.inspect_target_paths([])
        self.assertIsInstance(result, list)


class TestGeneratePreflightReport(unittest.TestCase):
    def setUp(self):
        self.pf = ZyeSystemPreflight()

    def test_report_returns_dict(self):
        rep = self.pf.generate_preflight_report(["d:/Zye/main.py"])
        self.assertIsInstance(rep, dict)

    def test_report_has_core_keys(self):
        rep = self.pf.generate_preflight_report(["d:/Zye/main.py"])
        for key in ("ram_used_pct", "cpu_load_pct", "disk_used_pct"):
            self.assertIn(key, rep, msg=f"Missing key '{key}' in preflight report")

    def test_report_ram_range(self):
        rep = self.pf.generate_preflight_report(["d:/Zye/main.py"])
        pct = rep.get("ram_used_pct", 0.0)
        self.assertGreaterEqual(pct, 0.0)
        self.assertLessEqual(pct, 100.0)

    def test_report_no_crash_missing_path(self):
        try:
            rep = self.pf.generate_preflight_report(["d:/Zye/nonexistent_path_xyz.txt"])
            self.assertIsInstance(rep, dict)
        except Exception as e:
            self.fail(f"Missing path in preflight report should not raise: {e}")


if __name__ == "__main__":
    unittest.main()
