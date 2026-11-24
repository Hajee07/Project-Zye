"""
Unit tests for Day 14 Travel Planning Intelligence Engine.
Verifies itinerary generation, budget tiers, packing checklists, and risk assessments.
"""

import os
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.database import get_db_connection
from zye_personal_assistant.travel_engine import TravelEngine


class TestDay14Travel(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_trv_test_")
        os.close(self._tmp_fd)
        self.engine = TravelEngine(db_path=self._tmp_path)

    def tearDown(self):
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_itinerary_structure_and_days(self):
        plan = self.engine.plan_itinerary(destination="Tokyo", days=4, purpose="Tech Conference", budget_tier="Moderate")
        self.assertEqual(plan["status"], "SUCCESS")
        self.assertEqual(plan["destination"], "Tokyo")
        self.assertEqual(plan["days"], 4)
        self.assertEqual(len(plan["itinerary"]), 4)

    def test_02_cost_breakdown_and_disclaimer(self):
        plan = self.engine.plan_itinerary(destination="London", days=3, budget_tier="Premium")
        costs = plan.get("estimated_costs", {})
        self.assertIn("lodging_total", costs)
        self.assertIn("transport_total", costs)
        self.assertIn("emergency_reserve", costs)
        self.assertIn("disclaimer", plan)
        self.assertIn("modeled approximations", plan["disclaimer"])

    def test_03_packing_checklist_and_risks(self):
        plan = self.engine.plan_itinerary(destination="Bengaluru", days=2)
        checklist = plan.get("packing_checklist", [])
        risks = plan.get("risks_and_mitigation", [])
        self.assertGreater(len(checklist), 3)
        self.assertEqual(len(risks), 3)

    def test_04_sqlite_persistence(self):
        self.engine.plan_itinerary(destination="Paris", days=5)
        conn = get_db_connection(self._tmp_path)
        try:
            row = conn.execute("SELECT destination, days, budget_tier FROM travel_plans WHERE destination = 'Paris';").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["destination"], "Paris")
            self.assertEqual(row["days"], 5)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
