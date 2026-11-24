"""
Unit tests for Day 14 Calendar Management Engine.
Verifies event creation, interval conflict detection, alternative slots, and daily schedule.
"""

import os
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.calendar_engine import CalendarEngine
from zye_personal_assistant.safety_gateway import SafetyGateway


class TestDay14Calendar(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_cal_test_")
        os.close(self._tmp_fd)
        sg = SafetyGateway(db_path=self._tmp_path)
        self.engine = CalendarEngine(db_path=self._tmp_path, safety_gateway=sg)

    def tearDown(self):
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_add_event_default_one_hour(self):
        res = self.engine.add_event(title="Strategy Sync", start_iso="2026-11-20T09:00:00")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("event_id", res)
        self.assertEqual(res["title"], "Strategy Sync")
        # Default 1-hour duration: end_iso should be 10:00:00
        self.assertIn("10:00:00", res["end_iso"])

    def test_02_conflict_detection_exact_overlap(self):
        self.engine.add_event(title="Meeting A", start_iso="2026-11-20T10:00:00", end_iso="2026-11-20T11:00:00")
        conflicts = self.engine.check_conflicts(start_iso="2026-11-20T10:00:00", end_iso="2026-11-20T11:00:00")
        self.assertTrue(conflicts["has_conflict"])
        self.assertEqual(conflicts["conflict_count"], 1)

    def test_03_conflict_detection_partial_overlap(self):
        self.engine.add_event(title="Meeting B", start_iso="2026-11-20T14:00:00", end_iso="2026-11-20T15:30:00")
        conflicts = self.engine.check_conflicts(start_iso="2026-11-20T14:30:00", end_iso="2026-11-20T16:00:00")
        self.assertTrue(conflicts["has_conflict"])
        self.assertGreater(len(conflicts["recommended_alternative_slots"]), 0)

    def test_04_adjacent_meetings_share_boundary_no_conflict(self):
        # 10:00 to 11:00
        self.engine.add_event(title="Meeting 1", start_iso="2026-11-20T10:00:00", end_iso="2026-11-20T11:00:00")
        # 11:00 to 12:00 (shares boundary at 11:00:00)
        conflicts = self.engine.check_conflicts(start_iso="2026-11-20T11:00:00", end_iso="2026-11-20T12:00:00")
        self.assertFalse(conflicts["has_conflict"], "Adjacent meetings sharing a boundary must not be treated as conflicting")

    def test_05_list_upcoming_and_daily_schedule(self):
        self.engine.add_event(title="Morning Standup", start_iso="2026-11-20T09:30:00", end_iso="2026-11-20T10:00:00")
        self.engine.add_event(title="Afternoon Retro", start_iso="2026-11-20T16:00:00", end_iso="2026-11-20T17:00:00")

        upcoming = self.engine.list_upcoming_events(from_iso="2026-11-20T08:00:00")
        self.assertEqual(len(upcoming), 2)

        daily = self.engine.get_daily_schedule("2026-11-20T12:00:00")
        self.assertEqual(len(daily), 2)

    def test_06_delete_event(self):
        add_res = self.engine.add_event(title="To be cancelled", start_iso="2026-11-20T18:00:00", end_iso="2026-11-20T19:00:00")
        event_id = add_res["event_id"]

        del_res = self.engine.delete_event(event_id=event_id)
        self.assertEqual(del_res["status"], "SUCCESS")

        # Verify event no longer appears in upcoming active events
        upcoming = self.engine.list_upcoming_events(from_iso="2026-11-20T17:00:00")
        active_ids = [e["id"] for e in upcoming]
        self.assertNotIn(event_id, active_ids)


if __name__ == "__main__":
    unittest.main()
