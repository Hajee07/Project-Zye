"""
Unit tests for GeminiUsageTracker — token telemetry, event persistence, and budget enforcement.
"""

import unittest
from gemini_usage_tracker import GeminiUsageTracker, UsageRecord


class TestGeminiUsageTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = GeminiUsageTracker(db_path=":memory:", auto_init=True)

    def test_01_record_usage_event(self):
        rec = UsageRecord(
            request_id="req_test_01",
            workload_id="INTERACTION",
            module_name="voice_loop",
            project_id="zye-project-01",
            key_alias="PROJECT_01",
            model_id="gemini-3.8-flash",
            thinking_level="LOW",
            input_tokens=150,
            output_tokens=75,
            thinking_tokens=25,
            total_tokens=250,
            cached_tokens=0,
            duration_seconds=0.45,
            status="SUCCESS",
        )
        self.tracker.record_event(rec)

        stats = self.tracker.get_token_statistics()
        self.assertEqual(stats["total_requests"], 1)
        self.assertEqual(stats["total_input_tokens"], 150)
        self.assertEqual(stats["total_output_tokens"], 75)
        self.assertEqual(stats["total_thinking_tokens"], 25)
        self.assertEqual(stats["grand_total_tokens"], 250)

    def test_02_budget_check_passes_when_under_limit(self):
        ok, reason = self.tracker.check_budget("zye-project-01")
        self.assertTrue(ok)
        self.assertEqual(reason, "OK")

    def test_03_budget_check_fails_when_exceeded(self):
        # Record massive usage to exceed default 5,000,000 daily limit
        rec = UsageRecord(
            request_id="req_heavy",
            workload_id="DEEP_TASK",
            module_name="test",
            project_id="zye-project-01",
            key_alias="PROJECT_01",
            model_id="gemini-3.8-flash",
            thinking_level="HIGH",
            total_tokens=6_000_000,
            status="SUCCESS",
        )
        self.tracker.record_event(rec)

        ok, reason = self.tracker.check_budget("zye-project-01")
        self.assertFalse(ok)
        self.assertIn("budget exceeded", reason.lower())


if __name__ == "__main__":
    unittest.main()
