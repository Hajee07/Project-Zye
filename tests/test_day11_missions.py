"""Unit tests for Zye Day 11 Mission Profiles & Adaptive Behavior."""

import json
import os
import pathlib
import tempfile
import threading
import unittest

from zye_autonomy.mission_profiles import MISSION_PROFILES, ZyeMissionController


class TestZyeMissionController(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.state_file = pathlib.Path(self.tmp_dir.name) / "test_mission_state.json"
        self.mc = ZyeMissionController(state_file=self.state_file)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_normal_assistant_profile(self):
        res = self.mc.set_mission("NORMAL_ASSISTANT")
        self.assertEqual(res["mission"], "NORMAL_ASSISTANT")
        self.assertEqual(res["risk_tolerance"], "MODERATE")
        self.assertEqual(res["resource_budget"], "BALANCED")

    def test_02_deep_engineering_profile(self):
        res = self.mc.set_mission("DEEP_ENGINEERING")
        self.assertEqual(res["mission"], "DEEP_ENGINEERING")
        self.assertEqual(res["risk_tolerance"], "LOW")
        self.assertEqual(res["resource_budget"], "HIGH_COMPUTE_ALLOWED")

    def test_03_stealth_battery_saver_profile(self):
        res = self.mc.set_mission("STEALTH_BATTERY_SAVER")
        self.assertEqual(res["mission"], "STEALTH_BATTERY_SAVER")
        self.assertEqual(res["risk_tolerance"], "CONSERVATIVE")
        self.assertEqual(res["resource_budget"], "ULTRA_LOW_POWER")

    def test_04_tactical_realtime_profile(self):
        res = self.mc.set_mission("TACTICAL_REALTIME")
        self.assertEqual(res["mission"], "TACTICAL_REALTIME")
        self.assertEqual(res["risk_tolerance"], "FAST_REFLEX")
        self.assertEqual(res["resource_budget"], "LOW_LATENCY_PRIORITY")

    def test_05_emergency_lockdown_profile(self):
        res = self.mc.set_mission("EMERGENCY_LOCKDOWN")
        self.assertEqual(res["mission"], "EMERGENCY_LOCKDOWN")
        self.assertEqual(res["risk_tolerance"], "ZERO_TRUST")
        self.assertEqual(res["resource_budget"], "CRITICAL_DEFENSE")

    def test_06_invalid_profile_raises(self):
        with self.assertRaises(ValueError):
            self.mc.set_mission("UNRECOGNIZED_MISSION_XYZ")

    def test_07_mission_persistence(self):
        self.mc.set_mission("DEEP_ENGINEERING", custom_objective="Compiling core")
        # Instantiate second controller referencing same file
        mc2 = ZyeMissionController(state_file=self.state_file)
        state = mc2.get_current_mission()
        self.assertEqual(state["mission"], "DEEP_ENGINEERING")
        self.assertEqual(state["custom_objective"], "Compiling core")

    def test_08_corrupt_json_recovery(self):
        # Write malformed JSON directly to state file
        self.state_file.write_text("CORRUPTED_NOT_VALID_JSON", encoding="utf-8")
        state = self.mc.load_mission()
        self.assertEqual(state["mission"], "NORMAL_ASSISTANT")

    def test_09_atomic_write_safety(self):
        self.mc.set_mission("TACTICAL_REALTIME")
        self.assertTrue(self.state_file.exists())
        data = json.loads(self.state_file.read_text(encoding="utf-8"))
        self.assertEqual(data["mission"], "TACTICAL_REALTIME")

    def test_10_concurrent_updates(self):
        errors = []

        def worker(mission_name: str):
            try:
                self.mc.set_mission(mission_name, f"Update by {mission_name}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=worker, args=(m,))
            for m in list(MISSION_PROFILES.keys())
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        final_state = self.mc.get_current_mission()
        self.assertIn(final_state["mission"], MISSION_PROFILES)

    def test_11_transition_history(self):
        self.mc.set_mission("DEEP_ENGINEERING", "Step 1")
        self.mc.set_mission("TACTICAL_REALTIME", "Step 2")
        history = self.mc.get_transition_history()
        self.assertGreaterEqual(len(history), 2)
        self.assertEqual(history[-1]["to_mission"], "TACTICAL_REALTIME")

    def test_12_suggest_mission_heuristics(self):
        self.assertEqual(self.mc.suggest_mission("Need to debug and patch Python script"), "DEEP_ENGINEERING")
        self.assertEqual(self.mc.suggest_mission("Battery level dropping rapidly unplugged"), "STEALTH_BATTERY_SAVER")
        self.assertEqual(self.mc.suggest_mission("Critical security breach attack detected"), "EMERGENCY_LOCKDOWN")
        self.assertEqual(self.mc.suggest_mission("Realtime telemetry streaming"), "TACTICAL_REALTIME")
        self.assertEqual(self.mc.suggest_mission("What is the weather today?"), "NORMAL_ASSISTANT")

    def test_13_recovery_to_default_on_missing_file(self):
        if self.state_file.exists():
            self.state_file.unlink()
        state = self.mc.load_mission()
        self.assertEqual(state["mission"], "NORMAL_ASSISTANT")


if __name__ == "__main__":
    unittest.main()
