"""Day 15 Unit Tests — Mission-Adaptive Behavior Controller."""
import json
import os
import tempfile
import unittest

from zye_autonomy.mission_controller import ZyeMissionController, MISSION_PROFILES


REQUIRED_PROFILES = [
    "NORMAL_ASSISTANT",
    "DEEP_ENGINEERING",
    "STEALTH_BATTERY_SAVER",
    "TACTICAL_REALTIME",
    "EMERGENCY_LOCKDOWN",
]

REQUIRED_PROFILE_KEYS = [
    "risk_tolerance", "resource_budget", "description",
    "premortem_required", "max_background_tasks",
]


class TestMissionProfiles(unittest.TestCase):
    def test_all_five_profiles_present(self):
        for name in REQUIRED_PROFILES:
            self.assertIn(name, MISSION_PROFILES, msg=f"Missing mission profile: {name}")

    def test_each_profile_has_required_keys(self):
        for name, profile in MISSION_PROFILES.items():
            for key in REQUIRED_PROFILE_KEYS:
                self.assertIn(key, profile, msg=f"Profile '{name}' missing key '{key}'")

    def test_premortem_required_is_bool(self):
        for name, profile in MISSION_PROFILES.items():
            self.assertIsInstance(profile["premortem_required"], bool,
                                  msg=f"'{name}'.premortem_required must be bool")

    def test_max_background_tasks_is_int(self):
        for name, profile in MISSION_PROFILES.items():
            self.assertIsInstance(profile["max_background_tasks"], int,
                                  msg=f"'{name}'.max_background_tasks must be int")

    def test_emergency_lockdown_zero_tasks(self):
        self.assertEqual(MISSION_PROFILES["EMERGENCY_LOCKDOWN"]["max_background_tasks"], 0)

    def test_emergency_lockdown_premortem_required(self):
        self.assertTrue(MISSION_PROFILES["EMERGENCY_LOCKDOWN"]["premortem_required"])

    def test_deep_engineering_premortem_required(self):
        self.assertTrue(MISSION_PROFILES["DEEP_ENGINEERING"]["premortem_required"])


class TestMissionControllerInit(unittest.TestCase):
    def test_creates_instance(self):
        mc = ZyeMissionController()
        self.assertIsNotNone(mc)

    def test_get_current_mission_returns_dict(self):
        mc = ZyeMissionController()
        cur = mc.get_current_mission()
        self.assertIsInstance(cur, dict)

    def test_get_current_mission_has_mission_key(self):
        mc = ZyeMissionController()
        cur = mc.get_current_mission()
        self.assertIn("mission", cur)

    def test_get_current_mission_has_risk_tolerance(self):
        mc = ZyeMissionController()
        cur = mc.get_current_mission()
        self.assertIn("risk_tolerance", cur)

    def test_default_mission_is_known_profile(self):
        mc = ZyeMissionController()
        cur = mc.get_current_mission()
        # Mission may default to any profile or last-persisted profile — just verify it's a known one
        self.assertIn(cur["mission"], REQUIRED_PROFILES)


class TestMissionSwitching(unittest.TestCase):
    def setUp(self):
        # Use a temp file so tests don't pollute actual state
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.mc = ZyeMissionController(state_file=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_switch_to_deep_engineering(self):
        self.mc.set_mission("DEEP_ENGINEERING")
        cur = self.mc.get_current_mission()
        self.assertEqual(cur["mission"], "DEEP_ENGINEERING")

    def test_switch_to_emergency_lockdown(self):
        self.mc.set_mission("EMERGENCY_LOCKDOWN")
        cur = self.mc.get_current_mission()
        self.assertEqual(cur["mission"], "EMERGENCY_LOCKDOWN")

    def test_switch_cycles_all_profiles(self):
        for profile in REQUIRED_PROFILES:
            self.mc.set_mission(profile)
            self.assertEqual(self.mc.get_current_mission()["mission"], profile)

    def test_invalid_profile_raises_or_returns_error(self):
        try:
            self.mc.set_mission("FAKE_NONEXISTENT_PROFILE")
            # If it didn't raise, the state must NOT have changed to invalid
            cur = self.mc.get_current_mission()
            self.assertIn(cur["mission"], REQUIRED_PROFILES)
        except (ValueError, KeyError):
            pass  # Raising is also valid

    def test_state_persists_to_file(self):
        self.mc.set_mission("TACTICAL_REALTIME")
        # Read file directly and verify
        with open(self.tmp.name, "r") as f:
            data = json.load(f)
        self.assertIn("mission", data)
        self.assertEqual(data["mission"], "TACTICAL_REALTIME")

    def test_corrupt_json_recovery(self):
        with open(self.tmp.name, "w") as f:
            f.write("{corrupt json!!!")
        # Creating a new controller with corrupt file should not raise
        try:
            mc2 = ZyeMissionController(state_file=self.tmp.name)
            cur = mc2.get_current_mission()
            self.assertIn("mission", cur)
        except Exception as e:
            self.fail(f"Corrupt JSON should not raise on init: {e}")


if __name__ == "__main__":
    unittest.main()
