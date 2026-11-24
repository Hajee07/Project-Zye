"""
Integration tests for Gemini Infrastructure with Day 14 Personal Assistant Workloads.
Verifies project slot 4 routing and data workflow interfaces.
"""

import unittest
from gemini_key_manager import GeminiKeyManager
from gemini_project_router import GeminiProjectRouter


class TestGeminiDay14Integration(unittest.TestCase):
    def setUp(self):
        self.km = GeminiKeyManager(db_path=":memory:", auto_load=False)
        self.router = GeminiProjectRouter(key_manager=self.km, db_path=":memory:")

    def test_01_personal_assistant_workload_routes_to_slot_4(self):
        pa_slot = self.router.route_workload("PERSONAL_ASSISTANT")
        self.assertEqual(pa_slot, 4)

    def test_02_automation_workload_routes_to_slot_4(self):
        auto_slot = self.router.route_workload("AUTOMATION")
        self.assertEqual(auto_slot, 4)

    def test_03_user_workflow_routes_to_slot_4(self):
        uw_slot = self.router.route_workload("USER_WORKFLOW")
        self.assertEqual(uw_slot, 4)

    def test_04_schedule_workload_routes_to_slot_4(self):
        sch_slot = self.router.route_workload("SCHEDULE")
        self.assertEqual(sch_slot, 4)


if __name__ == "__main__":
    unittest.main()
