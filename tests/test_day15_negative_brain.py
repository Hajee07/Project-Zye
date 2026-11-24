"""Day 15 Unit Tests — 100% Negative Pre-Mortem Brain & Adversarial FMEA."""
import asyncio
import inspect
import unittest

from zye_autonomy.premortem_engine import _generate_offline_fmea, ZyeNegativePreMortem


REQUIRED_FMEA_KEYS = [
    "overall_failure_risk",
    "predicted_problems",
    "requires_user_confirmation",
    "corrected_hardened_steps",
    "hidden_assumptions_broken",
]


class TestOfflineFMEAStructure(unittest.TestCase):
    def _fmea(self, task="Update config", steps=None, targets=None):
        return _generate_offline_fmea(
            task,
            steps or ["edit file"],
            targets or ["zye_config.toml"],
            {},
            "NORMAL_ASSISTANT",
        )

    def test_returns_dict(self):
        result = self._fmea()
        self.assertIsInstance(result, dict)

    def test_has_all_required_keys(self):
        result = self._fmea()
        for key in REQUIRED_FMEA_KEYS:
            self.assertIn(key, result, msg=f"FMEA missing key: '{key}'")

    def test_predicted_problems_is_list(self):
        result = self._fmea()
        self.assertIsInstance(result["predicted_problems"], list)

    def test_hardened_steps_is_list(self):
        result = self._fmea()
        self.assertIsInstance(result["corrected_hardened_steps"], list)

    def test_broken_assumptions_is_list(self):
        result = self._fmea()
        self.assertIsInstance(result["hidden_assumptions_broken"], list)

    def test_requires_user_confirmation_is_bool(self):
        result = self._fmea()
        self.assertIsInstance(result["requires_user_confirmation"], bool)

    def test_overall_risk_is_string(self):
        result = self._fmea()
        self.assertIsInstance(result["overall_failure_risk"], str)

    def test_overall_risk_valid_level(self):
        result = self._fmea()
        risk = result["overall_failure_risk"]
        self.assertIn(risk, ("LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"),
                      msg=f"Unexpected risk level: {risk}")


class TestDestructiveTaskRiskClassification(unittest.TestCase):
    def test_delete_task_high_or_critical_risk(self):
        result = _generate_offline_fmea(
            "Delete production database", ["rm -rf data/"], ["data/zye_assistant_db.sqlite"],
            {}, "NORMAL_ASSISTANT"
        )
        self.assertIn(result["overall_failure_risk"], ("HIGH", "CRITICAL"))

    def test_drop_table_high_or_critical_risk(self):
        result = _generate_offline_fmea(
            "Modify database schema", ["Drop table", "Recreate"], ["data/test.db"],
            {}, "NORMAL_ASSISTANT"
        )
        self.assertIn(result["overall_failure_risk"], ("HIGH", "CRITICAL"))

    def test_overwrite_requires_confirmation(self):
        result = _generate_offline_fmea(
            "Overwrite config file", ["overwrite"], ["zye_config.toml"],
            {}, "NORMAL_ASSISTANT"
        )
        self.assertTrue(result["requires_user_confirmation"])

    def test_destructive_task_has_predicted_problems(self):
        result = _generate_offline_fmea(
            "Delete file", ["rm"], ["data.db"], {}, "NORMAL_ASSISTANT"
        )
        self.assertGreater(len(result["predicted_problems"]), 0)


class TestFMEAMissionAwareness(unittest.TestCase):
    def test_emergency_lockdown_mission(self):
        result = _generate_offline_fmea(
            "Edit main.py", ["write"], ["main.py"],
            {}, "EMERGENCY_LOCKDOWN"
        )
        self.assertIsInstance(result, dict)
        self.assertIn("overall_failure_risk", result)

    def test_all_five_missions_no_crash(self):
        missions = [
            "NORMAL_ASSISTANT", "DEEP_ENGINEERING", "STEALTH_BATTERY_SAVER",
            "TACTICAL_REALTIME", "EMERGENCY_LOCKDOWN",
        ]
        for mission in missions:
            try:
                result = _generate_offline_fmea("Edit config", ["edit"], ["config.toml"], {}, mission)
                self.assertIsInstance(result, dict)
            except Exception as e:
                self.fail(f"Mission '{mission}' caused crash: {e}")


class TestNegativePreMortemClass(unittest.TestCase):
    def test_creates_instance(self):
        brain = ZyeNegativePreMortem()
        self.assertIsNotNone(brain)

    def test_run_audit_is_coroutine(self):
        brain = ZyeNegativePreMortem()
        self.assertTrue(
            hasattr(brain, "run_audit") and inspect.iscoroutinefunction(brain.run_audit),
            "ZyeNegativePreMortem.run_audit must be an async coroutine function"
        )

    def test_run_audit_offline_no_crash(self):
        """run_audit offline should return a dict (uses offline FMEA fallback)."""
        brain = ZyeNegativePreMortem()
        brain._client = None
        result = brain._call_gemini_structured_sync(
            task_description="Test audit",
            steps=["step1"],
            targets=["test.py"],
            preflight={},
            mission="NORMAL_ASSISTANT",
        )
        self.assertIsInstance(result, dict)
        self.assertIn("overall_failure_risk", result)


if __name__ == "__main__":
    unittest.main()
