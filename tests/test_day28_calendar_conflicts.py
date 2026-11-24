"""
Unit and integration tests for Day 28 Conflict Detection Engine.
Tests half-open intervals [start, end), touching boundary allowance,
conflict blocking, multiple overlapping detection, and force_override.
"""

import os
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.calendar.calendar_database import initialize_calendar_database
from zye_personal_assistant.calendar.calendar_event_engine import CalendarEventEngine
from zye_personal_assistant.calendar.calendar_models import CalendarEventCreate, CalendarEventUpdate


class TestDay28CalendarConflicts(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_d28_conflicts_")
        os.close(self._tmp_fd)
        initialize_calendar_database(self._tmp_path)
        self.engine = CalendarEventEngine(db_path=self._tmp_path, default_tz="Asia/Kolkata")

        # Seed initial meeting: 10:00 to 11:00
        res = self.engine.create_event(CalendarEventCreate(
            title="Core Meeting",
            start_time="2026-11-25T10:00:00",
            duration_minutes=60,
        ))
        self.assertEqual(res.status, "SUCCESS")
        self.base_event_id = res.event_id

    def tearDown(self):
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_touching_boundary_after_is_not_conflict(self):
        # 11:00 to 12:00 starts exactly when Core Meeting ends
        res = self.engine.create_event(CalendarEventCreate(
            title="Follow-up Meeting",
            start_time="2026-11-25T11:00:00",
            duration_minutes=60,
        ))
        self.assertEqual(res.status, "SUCCESS", "Adjacent meeting sharing end/start boundary must succeed")

    def test_02_touching_boundary_before_is_not_conflict(self):
        # 09:00 to 10:00 ends exactly when Core Meeting starts
        res = self.engine.create_event(CalendarEventCreate(
            title="Pre-briefing",
            start_time="2026-11-25T09:00:00",
            duration_minutes=60,
        ))
        self.assertEqual(res.status, "SUCCESS", "Adjacent meeting sharing end/start boundary must succeed")

    def test_03_exact_overlap_is_blocked(self):
        # 10:00 to 11:00 exact collision
        res = self.engine.create_event(CalendarEventCreate(
            title="Duplicate Time Slot",
            start_time="2026-11-25T10:00:00",
            duration_minutes=60,
        ))
        self.assertEqual(res.status, "CONFLICT_BLOCKED")
        self.assertEqual(res.error_code, "CALENDAR_CONFLICT")
        self.assertGreater(len(res.conflicts), 0)
        self.assertGreater(len(res.suggested_slots), 0)

    def test_04_interior_overlap_is_blocked(self):
        # 10:15 to 10:45 inside 10:00 to 11:00
        res = self.engine.create_event(CalendarEventCreate(
            title="Mid-Hour Chat",
            start_time="2026-11-25T10:15:00",
            duration_minutes=30,
        ))
        self.assertEqual(res.status, "CONFLICT_BLOCKED")
        self.assertEqual(res.conflicts[0]["title"], "Core Meeting")

    def test_05_left_overlap_is_blocked(self):
        # 09:30 to 10:30 overlaps first 30 minutes
        res = self.engine.create_event(CalendarEventCreate(
            title="Early Overlap",
            start_time="2026-11-25T09:30:00",
            duration_minutes=60,
        ))
        self.assertEqual(res.status, "CONFLICT_BLOCKED")

    def test_06_right_overlap_is_blocked(self):
        # 10:30 to 11:30 overlaps second 30 minutes
        res = self.engine.create_event(CalendarEventCreate(
            title="Late Overlap",
            start_time="2026-11-25T10:30:00",
            duration_minutes=60,
        ))
        self.assertEqual(res.status, "CONFLICT_BLOCKED")

    def test_07_enclosing_overlap_is_blocked(self):
        # 09:00 to 12:00 completely covers 10:00 to 11:00
        res = self.engine.create_event(CalendarEventCreate(
            title="Long Session",
            start_time="2026-11-25T09:00:00",
            duration_minutes=180,
        ))
        self.assertEqual(res.status, "CONFLICT_BLOCKED")

    def test_08_force_override_bypasses_conflict(self):
        res = self.engine.create_event(
            CalendarEventCreate(
                title="Urgent Executive Override",
                start_time="2026-11-25T10:00:00",
                duration_minutes=60,
            ),
            force_override=True,
        )
        self.assertEqual(res.status, "SUCCESS")
        self.assertIsNotNone(res.event_id)

    def test_09_updating_self_does_not_conflict_with_self(self):
        # Updating notes or title on the base event should succeed
        res = self.engine.update_event(CalendarEventUpdate(
            event_id=self.base_event_id,
            title="Core Meeting (Updated)",
            notes="Added agenda",
        ))
        self.assertEqual(res.status, "SUCCESS")


if __name__ == "__main__":
    unittest.main()
