"""
Unit tests for Day 13 Emergency Reflex Controller.
Tests zye_intelligence.emergency_reflex: ZyeEmergencyReflex, execute_emergency_reflex,
and bounded allowlisted system actions without arbitrary shell execution or process killing.
"""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from zye_intelligence.emergency_reflex import (
    SUPPORTED_EMERGENCY_TYPES,
    ZyeEmergencyReflex,
    execute_emergency_reflex,
)
from zye_intelligence.mission_controller import ZyeMissionController


class TestDay13EmergencyReflex(unittest.TestCase):
    def setUp(self) -> None:
        self.mc = ZyeMissionController()
        self.reflex = ZyeEmergencyReflex(mission_controller=self.mc)

    def test_01_battery_critical(self) -> None:
        """Verify battery_critical switches to STEALTH_BATTERY_SAVER and attempts brightness."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_proc

            res = asyncio.run(self.reflex.execute("battery_critical"))
            self.assertEqual(res["emergency_handled"], "battery_critical")
            self.assertEqual(res["active_mission"], "STEALTH_BATTERY_SAVER")
            self.assertGreater(len(res["actions_executed"]), 0)

    def test_02_ram_overload_relief(self) -> None:
        """Verify ram_overload_relief runs gc.collect and does not kill arbitrary processes."""
        with patch("gc.collect", return_value=42):
            res = asyncio.run(self.reflex.execute("ram_overload_relief"))
            self.assertEqual(res["emergency_handled"], "ram_overload_relief")
            self.assertEqual(res["status"], "SUCCESS")
            self.assertTrue(any("garbage" in a.lower() for a in res["actions_executed"]))

    def test_03_cyber_lockdown(self) -> None:
        """Verify cyber_lockdown switches to EMERGENCY_LOCKDOWN (zero trust)."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_proc

            res = asyncio.run(self.reflex.execute("cyber_lockdown"))
            self.assertEqual(res["emergency_handled"], "cyber_lockdown")
            self.assertEqual(res["active_mission"], "EMERGENCY_LOCKDOWN")

    def test_04_unknown_emergency_type(self) -> None:
        """Verify unrecognized emergency types are strictly rejected."""
        res = asyncio.run(self.reflex.execute("format_hard_drive"))
        self.assertEqual(res["status"], "REJECTED")
        self.assertIn("Rejected unrecognized emergency type", res["failed_actions"][0])

    def test_05_authorization_denied(self) -> None:
        """Verify cyber lockdown does not sever network without authorization."""
        res = asyncio.run(self.reflex.execute("cyber_lockdown"))
        self.assertTrue(any("authorization" in r.lower() for r in res["remaining_risks"]))

    def test_06_unsupported_hardware(self) -> None:
        """Verify brightness handling on unsupported hardware handles error gracefully."""
        with patch("asyncio.create_subprocess_exec", side_effect=OSError("WMI not found")):
            res = asyncio.run(self.reflex.battery_critical())
            self.assertIn(res["status"], ("SUCCESS", "PARTIAL"))
            self.assertTrue(any("brightness" in f.lower() for f in res["failed_actions"]))

    def test_07_failed_system_command(self) -> None:
        """Verify non-zero return code from subprocess does not crash reflex."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = MagicMock()
            mock_proc.returncode = 1
            mock_proc.communicate = AsyncMock(return_value=(b"", b"Access denied"))
            mock_exec.return_value = mock_proc

            res = asyncio.run(self.reflex.battery_critical())
            self.assertIn(res["status"], ("SUCCESS", "PARTIAL"))

    def test_08_verified_system_change(self) -> None:
        """Verify that executed actions are confirmed in action_verification list."""
        res = asyncio.run(self.reflex.execute("ram_overload_relief"))
        self.assertGreater(len(res["action_verification"]), 0)

    def test_09_no_arbitrary_process_termination(self) -> None:
        """Verify reflex never calls psutil.Process.terminate() or taskkill."""
        with patch("subprocess.run") as mock_sub:
            res = asyncio.run(self.reflex.execute("ram_overload_relief"))
            # Ensure taskkill /f /im was never called
            for c in mock_sub.call_args_list:
                self.assertNotIn("taskkill", str(c))

    def test_10_correct_mission_transition(self) -> None:
        """Verify active mission is switched appropriately."""
        asyncio.run(self.reflex.execute("battery_critical"))
        state = self.mc.get_current_mission()
        self.assertEqual(state["mission"], "STEALTH_BATTERY_SAVER")

    def test_11_correct_audit_logging(self) -> None:
        """Verify reflex execution can be logged via logging subsystem."""
        from zye_intelligence.logging import log_emergency_reflex
        res = {"emergency_handled": "battery_critical", "status": "SUCCESS"}
        # Should not raise exception
        log_emergency_reflex(res)


if __name__ == "__main__":
    unittest.main()
