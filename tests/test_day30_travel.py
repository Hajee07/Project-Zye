"""
Day 30 Test Suite: Intelligent Travel Planning Engine
Tests destination and duration validation, budget tiers, purpose tailoring,
packing checklists, transit buffers, travel risk assessments, and calendar conflict checks.
"""

import os
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.database import init_assistant_database, get_db_connection
from zye_personal_assistant.calendar_engine import CalendarEngine
from zye_personal_assistant.travel_engine import TravelEngine
from zye_personal_assistant.safety_gateway import SafetyGateway


class TestDay30TravelPlanning(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_test_travel_")
        os.close(self._tmp_fd)
        self.db_path = Path(self._tmp_path)
        init_assistant_database(self.db_path)
        self.engine = TravelEngine(db_path=self.db_path)
        self.calendar = CalendarEngine(db_path=self.db_path)

    def tearDown(self):
        try:
            self.db_path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_valid_trip_planning(self):
        """Generates a complete day-by-day itinerary with budget and packing checklist."""
        res = self.engine.plan_itinerary(
            destination="Chennai",
            days=3,
            purpose="Exploration",
            budget_tier="Moderate",
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["destination"], "Chennai")
        self.assertEqual(res["days"], 3)
        self.assertEqual(len(res["itinerary"]), 3)
        self.assertIn("estimated_costs", res)
        self.assertGreater(res["estimated_costs"]["estimated_grand_total"], 0)
        self.assertGreaterEqual(len(res["packing_checklist"]), 5)
        self.assertGreaterEqual(len(res["risks_and_mitigation"]), 3)
        self.assertFalse(res["is_live_verified"])

    def test_02_empty_destination_rejection(self):
        """Empty destination returns error with TRAVEL_INVALID_DESTINATION code."""
        res = self.engine.plan_itinerary(destination="   ", days=3)
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res.get("error_code"), "TRAVEL_INVALID_DESTINATION")

    def test_03_zero_and_negative_days_rejection(self):
        """Zero or negative days returns error with TRAVEL_INVALID_DURATION code."""
        res_zero = self.engine.plan_itinerary(destination="Bangalore", days=0)
        self.assertEqual(res_zero["status"], "ERROR")
        self.assertEqual(res_zero.get("error_code"), "TRAVEL_INVALID_DURATION")

        res_neg = self.engine.plan_itinerary(destination="Bangalore", days=-2)
        self.assertEqual(res_neg["status"], "ERROR")
        self.assertEqual(res_neg.get("error_code"), "TRAVEL_INVALID_DURATION")

    def test_04_budget_tiers(self):
        """Different budget tiers scale the estimated costs predictably."""
        res_econ = self.engine.plan_itinerary(destination="Singapore", days=4, budget_tier="Economy")
        res_mod = self.engine.plan_itinerary(destination="Singapore", days=4, budget_tier="Moderate")
        res_prem = self.engine.plan_itinerary(destination="Singapore", days=4, budget_tier="Premium")

        cost_econ = res_econ["estimated_costs"]["estimated_grand_total"]
        cost_mod = res_mod["estimated_costs"]["estimated_grand_total"]
        cost_prem = res_prem["estimated_costs"]["estimated_grand_total"]

        self.assertLess(cost_econ, cost_mod)
        self.assertLess(cost_mod, cost_prem)

    def test_05_purpose_tailoring(self):
        """Business purpose includes professional gear in packing checklist."""
        res_biz = self.engine.plan_itinerary(
            destination="Tokyo",
            days=5,
            purpose="Business Conference",
        )
        checklist_str = " ".join(res_biz["packing_checklist"]).lower()
        self.assertTrue("business" in checklist_str or "portfolio" in checklist_str or "laptop" in checklist_str)

    def test_06_calendar_conflict_detection(self):
        """Travel planner detects overlapping calendar events when start date is given."""
        # Add an existing meeting on 2026-12-05
        self.calendar.add_event(
            title="Quarterly Board Meeting",
            start_iso="2026-12-05T10:00:00+05:30",
            end_iso="2026-12-05T12:00:00+05:30",
        )

        res = self.engine.plan_itinerary(
            destination="Delhi",
            days=4,
            start_date_iso="2026-12-04",
            check_calendar_conflicts=True,
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertGreaterEqual(res.get("calendar_conflicts_detected", 0), 1)
        self.assertTrue(any("Board Meeting" in ev["title"] for ev in res.get("conflicting_events", [])))


if __name__ == "__main__":
    unittest.main()
