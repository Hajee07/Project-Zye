"""
Unit tests for Day 13 Dynamic Mission Profiles & Persistence.
Tests zye_intelligence.mission_controller: ZyeMissionController, MISSION_PROFILES,
atomic JSON state management, hysteresis dampening, and corruption recovery.
"""

from __future__ import annotations

import json
import pathlib
import tempfile
import time
import unittest

from zye_intelligence.mission_controller import (
    MISSION_PROFILES,
    ZyeMissionController,
    get_current_mission,
    set_mission_mode,
)


class TestDay13MissionProfiles(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_file = pathlib.Path(self.temp_dir.name) / "test_mission_state.json"
        self.mc = ZyeMissionController(state_file=self.state_file, hysteresis_seconds=0.1)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_01_normal_assistant_profile(self) -> None:
        """Verify NORMAL_ASSISTANT profile metadata."""
        p = MISSION_PROFILES["NORMAL_ASSISTANT"]
        self.assertEqual(p["risk_tolerance"], "MODERATE")
        self.assertEqual(p["resource_budget"], "BALANCED")
        self.assertFalse(p["premortem_required"])

    def test_02_deep_engineering_profile(self) -> None:
        """Verify DEEP_ENGINEERING profile metadata."""
        p = MISSION_PROFILES["DEEP_ENGINEERING"]
        self.assertIn("LOW", p["risk_tolerance"])
        self.assertEqual(p["resource_budget"], "HIGH_COMPUTE_ALLOWED")
        self.assertTrue(p["premortem_required"])

    def test_03_stealth_battery_saver_profile(self) -> None:
        """Verify STEALTH_BATTERY_SAVER profile metadata."""
        p = MISSION_PROFILES["STEALTH_BATTERY_SAVER"]
        self.assertEqual(p["risk_tolerance"], "CONSERVATIVE")
        self.assertEqual(p["resource_budget"], "ULTRA_LOW_POWER")
        self.assertTrue(p["premortem_required"])

    def test_04_tactical_realtime_profile(self) -> None:
        """Verify TACTICAL_REALTIME profile metadata."""
        p = MISSION_PROFILES["TACTICAL_REALTIME"]
        self.assertEqual(p["risk_tolerance"], "FAST_REFLEX")
        self.assertEqual(p["resource_budget"], "LOW_LATENCY_PRIORITY")

    def test_05_emergency_lockdown_profile(self) -> None:
        """Verify EMERGENCY_LOCKDOWN profile metadata."""
        p = MISSION_PROFILES["EMERGENCY_LOCKDOWN"]
        self.assertEqual(p["risk_tolerance"], "ZERO_TRUST")
        self.assertEqual(p["resource_budget"], "CRITICAL_DEFENSE")
        self.assertTrue(p["premortem_required"])

    def test_06_invalid_mission_rejected(self) -> None:
        """Verify that unknown mission names raise ValueError."""
        with self.assertRaises(ValueError):
            self.mc.set_mission("ULTRA_HACKER_MODE")

    def test_07_mission_persistence(self) -> None:
        """Verify atomic JSON persistence across controller reloads."""
        self.mc.set_mission("DEEP_ENGINEERING", custom_objective="CAD Simulation", force=True)
        self.assertTrue(self.state_file.exists())

        # Reload with new instance
        new_mc = ZyeMissionController(state_file=self.state_file)
        state = new_mc.get_current_mission()
        self.assertEqual(state["mission"], "DEEP_ENGINEERING")
        self.assertEqual(state["custom_objective"], "CAD Simulation")

    def test_08_corrupt_mission_json(self) -> None:
        """Verify that corrupted JSON is detected and preserved as .corrupt."""
        # Initialize valid file first
        self.mc.set_mission("NORMAL_ASSISTANT", force=True)
        # Corrupt file
        self.state_file.write_text("CORRUPTED_NOT_JSON {{{", encoding="utf-8")

        recovered = self.mc.load_mission()
        self.assertEqual(recovered["mission"], "NORMAL_ASSISTANT")
        corrupt_backup = self.state_file.with_suffix(".json.corrupt")
        self.assertTrue(corrupt_backup.exists())

    def test_09_mission_restoration_from_backup(self) -> None:
        """Verify that valid backup is used during corruption recovery."""
        self.mc.set_mission("DEEP_ENGINEERING", force=True)
        # Ensure backup exists
        backup_file = self.state_file.with_suffix(".json.bak")
        self.assertTrue(backup_file.exists())

        # Damage active file
        self.state_file.write_text("NOT_JSON", encoding="utf-8")
        recovered = self.mc.load_mission()
        self.assertEqual(recovered["mission"], "DEEP_ENGINEERING")

    def test_10_automatic_transition(self) -> None:
        """Verify automatic transition recorded in history."""
        self.mc.set_mission("TACTICAL_REALTIME", transition_reason="Urgent telemetry", force=True)
        state = self.mc.get_current_mission()
        self.assertEqual(state["mission"], "TACTICAL_REALTIME")
        self.assertEqual(len(self.mc._transition_history), 1)

    def test_11_hysteresis(self) -> None:
        """Verify hysteresis dampens rapid consecutive transitions."""
        mc_hyst = ZyeMissionController(state_file=self.state_file, hysteresis_seconds=10.0)
        mc_hyst.set_mission("DEEP_ENGINEERING", force=True)

        # Attempt immediate switch without force
        res = mc_hyst.set_mission("TACTICAL_REALTIME", force=False)
        # Should stay in DEEP_ENGINEERING
        self.assertEqual(res["mission"], "DEEP_ENGINEERING")

    def test_12_manual_override(self) -> None:
        """Verify force=True overrides hysteresis immediately."""
        mc_hyst = ZyeMissionController(state_file=self.state_file, hysteresis_seconds=10.0)
        mc_hyst.set_mission("DEEP_ENGINEERING", force=True)
        # Force switch
        res = mc_hyst.set_mission("STEALTH_BATTERY_SAVER", force=True)
        self.assertEqual(res["mission"], "STEALTH_BATTERY_SAVER")


if __name__ == "__main__":
    unittest.main()
