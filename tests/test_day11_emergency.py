"""Unit tests for Zye Day 11 Emergency Reflex Controller."""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from zye_autonomy.emergency_reflex import ZyeEmergencyReflex


class TestZyeEmergencyReflex(unittest.TestCase):
    def setUp(self):
        self.mock_mission = MagicMock()
        self.config = {
            "cyber_lockdown_enabled": True,
            "require_verified_security_signal": True,
        }
        self.refl = ZyeEmergencyReflex(mission_controller=self.mock_mission, config=self.config)

    def test_01_unknown_emergency_type_rejected(self):
        async def _run():
            res = await self.refl.execute("arbitrary_hacker_command")
            self.assertEqual(res["status"], "REJECTED")
            self.assertEqual(len(res["rapid_actions_executed"]), 0)
            self.assertIn("Rejected unrecognized emergency type", res["failed_actions"][0])
        asyncio.run(_run())

    def test_02_battery_critical_reflex(self):
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0, stdout="15", stderr="")

            async def _run():
                res = await self.refl.execute("battery_critical")
                self.assertIn(res["status"], ["SUCCESS", "PARTIAL"])
                self.mock_mission.set_mission.assert_called_with(
                    "STEALTH_BATTERY_SAVER",
                    custom_objective="Emergency reflex: Battery critically low (<=8%)",
                )
                self.assertTrue(any("STEALTH_BATTERY_SAVER" in a for a in res["rapid_actions_executed"]))
            asyncio.run(_run())

    def test_03_brightness_control_failure_handled(self):
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=1, stdout="", stderr="WMI unsupported")

            async def _run():
                res = await self.refl.execute("battery_critical")
                self.assertIn(res["status"], ["PARTIAL", "SUCCESS"])
                self.assertTrue(any("Brightness control unsupported" in v for v in res["verification_results"]))
            asyncio.run(_run())

    def test_04_ram_overload_relief(self):
        mock_vm = MagicMock(percent=92.0, available=1 * (1024**3))
        with patch("psutil.virtual_memory", return_value=mock_vm):
            async def _run():
                res = await self.refl.execute("ram_overload_relief")
                self.assertIn(res["status"], ["SUCCESS", "PARTIAL"])
                self.mock_mission.set_mission.assert_called_with(
                    "STEALTH_BATTERY_SAVER",
                    custom_objective="Emergency reflex: RAM overload relief (low-resource mode)",
                )
                # Ensure user processes protection is guaranteed
                self.assertTrue(any("zero user applications terminated" in a for a in res["rapid_actions_executed"]))
            asyncio.run(_run())

    def test_05_no_user_process_termination(self):
        # Verify that emergency controller does not contain process kill logic
        self.assertFalse(hasattr(self.refl, "terminate_process"))
        self.assertFalse(hasattr(self.refl, "kill_process"))

    def test_06_cyber_lockdown_enabled(self):
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0, stdout="State: ON", stderr="")

            async def _run():
                res = await self.refl.execute("cyber_lockdown")
                self.assertIn(res["status"], ["SUCCESS", "PARTIAL"])
                self.mock_mission.set_mission.assert_called_with(
                    "EMERGENCY_LOCKDOWN",
                    custom_objective="Emergency reflex: Cyber lockdown activated",
                )
                self.assertTrue(any("Windows Firewall" in a for a in res["rapid_actions_executed"]))
                self.assertTrue(any("DNS" in a for a in res["rapid_actions_executed"]))
            asyncio.run(_run())

    def test_07_cyber_lockdown_disabled_in_config(self):
        disabled_refl = ZyeEmergencyReflex(
            mission_controller=self.mock_mission,
            config={"cyber_lockdown_enabled": False},
        )
        async def _run():
            res = await disabled_refl.execute("cyber_lockdown")
            self.assertEqual(res["status"], "REJECTED")
            self.assertIn("disabled in system configuration", res["failed_actions"][0])
        asyncio.run(_run())

    def test_08_subprocess_timeout_handling(self):
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
            async def _run():
                res = await self.refl.execute("cyber_lockdown")
                self.assertIn(res["status"], ["PARTIAL", "SUCCESS"])
                self.assertTrue(any("timed out" in f for f in res["failed_actions"]))
            asyncio.run(_run())

    def test_09_emergency_result_schema_fields(self):
        async def _run():
            res = await self.refl.execute("unknown_type")
            self.assertIn("emergency_handled", res)
            self.assertIn("rapid_actions_executed", res)
            self.assertIn("verification_results", res)
            self.assertIn("failed_actions", res)
            self.assertIn("timestamp", res)
            self.assertIn("status", res)
        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
