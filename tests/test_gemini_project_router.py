"""
Unit tests for GeminiProjectRouter — Workload-to-project routing, rate limiting, and no-quota-evasion rule.
"""

import unittest
from gemini_key_manager import GeminiKeyManager
from gemini_project_router import GeminiProjectRouter, DEFAULT_WORKLOAD_ROUTING


class TestGeminiProjectRouter(unittest.TestCase):
    def setUp(self):
        km = GeminiKeyManager(db_path=":memory:", auto_load=False)
        self.router = GeminiProjectRouter(key_manager=km, db_path=":memory:", allow_cross_project_fallback=False)

    def test_01_canonical_workload_routing(self):
        self.assertEqual(self.router.route_workload("INTERACTION"), 1)
        self.assertEqual(self.router.route_workload("CONVERSATION"), 1)
        self.assertEqual(self.router.route_workload("MCP_ORCHESTRATOR"), 2)
        self.assertEqual(self.router.route_workload("TOOL_ROUTING"), 2)
        self.assertEqual(self.router.route_workload("PREMORTEM"), 3)
        self.assertEqual(self.router.route_workload("NEGATIVE_BRAIN"), 3)
        self.assertEqual(self.router.route_workload("PERSONAL_ASSISTANT"), 4)
        self.assertEqual(self.router.route_workload("AUTOMATION"), 4)
        self.assertEqual(self.router.route_workload("WATCHDOG"), 5)
        self.assertEqual(self.router.route_workload("PREFLIGHT"), 5)
        self.assertEqual(self.router.route_workload("EMERGENCY_REFLEX"), 6)
        self.assertEqual(self.router.route_workload("SELF_REPAIR"), 6)
        self.assertEqual(self.router.route_workload("TASK_DECOMPOSITION"), 7)
        self.assertEqual(self.router.route_workload("PARALLEL_WORKERS"), 7)

    def test_02_unknown_workload_routes_to_default_slot_1(self):
        self.assertEqual(self.router.route_workload("TOTALLY_UNKNOWN_WORKLOAD_XYZ"), 1)

    def test_03_custom_workload_registration(self):
        ok = self.router.register_workload("CUSTOM_PIPELINE", 4)
        self.assertTrue(ok)
        self.assertEqual(self.router.route_workload("CUSTOM_PIPELINE"), 4)

    def test_04_invalid_slot_registration_rejected(self):
        self.assertFalse(self.router.register_workload("INVALID_SLOT", 99))
        self.assertFalse(self.router.register_workload("INVALID_SLOT", 0))

    def test_05_strictly_prohibits_cross_project_quota_fallback(self):
        self.assertFalse(self.router.allow_cross_project_fallback)

    def test_06_rate_limited_slot_is_unavailable(self):
        self.router.mark_rate_limited(2, retry_after_seconds=30.0)
        avail, reason = self.router.is_slot_available(2)
        self.assertFalse(avail)
        self.assertIn("rate limited", reason.lower())

    def test_07_clear_rate_limit(self):
        self.router.mark_rate_limited(3, retry_after_seconds=30.0)
        self.router.clear_rate_limit(3)
        # Note: Slot 3 might be unconfigured in mock KM, but rate limit is cleared
        rl = self.router._rate_limits[3]
        self.assertEqual(rl.rate_limited_until, 0.0)

    def test_08_get_project_status(self):
        status_list = self.router.get_all_projects_status()
        self.assertEqual(len(status_list), 7)
        slot_ids = [p["slot_id"] for p in status_list]
        self.assertEqual(slot_ids, [1, 2, 3, 4, 5, 6, 7])


if __name__ == "__main__":
    unittest.main()
