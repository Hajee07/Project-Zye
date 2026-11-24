"""Day 15 Unit Tests — Bounded Emergency Reflex System."""
import asyncio
import unittest

from zye_autonomy.emergency_reflexes import ZyeEmergencyReflex, SUPPORTED_EMERGENCY_TYPES


class TestEmergencyReflexInit(unittest.TestCase):
    def test_creates_instance(self):
        er = ZyeEmergencyReflex()
        self.assertIsNotNone(er)

    def test_cyber_lockdown_enabled_default_true(self):
        er = ZyeEmergencyReflex()
        self.assertTrue(er.cyber_lockdown_enabled)

    def test_cyber_lockdown_can_be_disabled(self):
        er = ZyeEmergencyReflex(config={"cyber_lockdown_enabled": False})
        self.assertFalse(er.cyber_lockdown_enabled)

    def test_brightness_target_is_int(self):
        er = ZyeEmergencyReflex()
        self.assertIsInstance(er.brightness_target, int)

    def test_brightness_target_default(self):
        er = ZyeEmergencyReflex()
        self.assertEqual(er.brightness_target, 15)

    def test_custom_brightness_target(self):
        er = ZyeEmergencyReflex(config={"brightness_target": 30})
        self.assertEqual(er.brightness_target, 30)


class TestSupportedEmergencyTypes(unittest.TestCase):
    def test_supported_types_is_iterable(self):
        self.assertTrue(hasattr(SUPPORTED_EMERGENCY_TYPES, "__iter__"))

    def test_contains_ram_overload_relief(self):
        self.assertIn("ram_overload_relief", SUPPORTED_EMERGENCY_TYPES)

    def test_contains_battery_critical(self):
        self.assertIn("battery_critical", SUPPORTED_EMERGENCY_TYPES)

    def test_contains_cyber_lockdown(self):
        self.assertIn("cyber_lockdown", SUPPORTED_EMERGENCY_TYPES)

    def test_minimum_three_types(self):
        self.assertGreaterEqual(len(SUPPORTED_EMERGENCY_TYPES), 3)


class TestReflexRamOverload(unittest.TestCase):
    def test_ram_overload_relief_runs(self):
        """ram_overload_relief should complete without crashing."""
        er = ZyeEmergencyReflex()
        try:
            result = asyncio.run(er.ram_overload_relief())
            self.assertIsInstance(result, dict)
        except Exception as e:
            self.fail(f"ram_overload_relief() raised unexpectedly: {e}")

    def test_ram_overload_result_has_status(self):
        er = ZyeEmergencyReflex()
        result = asyncio.run(er.ram_overload_relief())
        self.assertIn("status", result)


class TestReflexBatteryCritical(unittest.TestCase):
    def test_battery_critical_runs(self):
        er = ZyeEmergencyReflex()
        async def _mock_run(cmd, timeout=5.0):
            return (0, "Mocked output", "")
        er._run_command = _mock_run
        try:
            result = asyncio.run(er.battery_critical())
            self.assertIsInstance(result, dict)
            self.assertIn("status", result)
        except Exception as e:
            self.fail(f"battery_critical() raised unexpectedly: {e}")


class TestCyberLockdown(unittest.TestCase):
    def test_cyber_lockdown_blocked_when_disabled(self):
        er = ZyeEmergencyReflex(config={"cyber_lockdown_enabled": False})
        result = asyncio.run(er.cyber_lockdown())
        self.assertIsInstance(result, dict)
        status = result.get("status", "")
        self.assertNotEqual(status, "ENGAGED_LOCKDOWN",
                            "Lockdown should NOT engage when disabled")

    def test_cyber_lockdown_enabled_returns_dict(self):
        er = ZyeEmergencyReflex(config={"cyber_lockdown_enabled": True})
        async def _mock_run(cmd, timeout=5.0):
            return (0, "Mocked output", "")
        er._run_command = _mock_run
        try:
            result = asyncio.run(er.cyber_lockdown())
            self.assertIsInstance(result, dict)
            self.assertIn("status", result)
        except Exception as e:
            self.fail(f"cyber_lockdown() raised unexpectedly: {e}")


if __name__ == "__main__":
    unittest.main()
