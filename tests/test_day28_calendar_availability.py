"""
Unit and integration tests for Day 28 Calendar Availability & Free-Slot Engine.
Tests free-slot discovery, working-hours constraints, alternative slot recommendations,
and gap identification between scheduled meetings.
"""

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from zye_personal_assistant.calendar.calendar_availability_engine import (
    find_free_time_slots,
    suggest_alternative_slots,
)
from zye_personal_assistant.calendar.calendar_database import initialize_calendar_database, get_db_connection
from zye_personal_assistant.calendar.calendar_event_engine import CalendarEventEngine
from zye_personal_assistant.calendar.calendar_models import CalendarEventCreate
from zye_personal_assistant.calendar.calendar_timezone_engine import convert_local_to_utc


class TestDay28CalendarAvailability(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_d28_avail_")
        os.close(self._tmp_fd)
        initialize_calendar_database(self._tmp_path)
        self.engine = CalendarEventEngine(db_path=self._tmp_path, default_tz="Asia/Kolkata")

    def tearDown(self):
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_free_slots_in_empty_day(self):
        conn = get_db_connection(self._tmp_path)
        try:
            slots = find_free_time_slots(
                conn=conn,
                target_date_iso="2026-11-25",
                work_start_hour=9,
                work_end_hour=18,
                min_slot_minutes=30,
                timezone_id="Asia/Kolkata",
                max_suggestions=5,
            )
            self.assertEqual(len(slots), 5)
            self.assertEqual(slots[0]["duration_minutes"], 30)
            self.assertIn("09:00 AM", slots[0]["slot_label"])
        finally:
            conn.close()

    def test_02_free_slots_with_intermediate_meetings(self):
        # Book 10:00-11:00 and 14:00-15:00 on 2026-11-25
        self.engine.create_event(CalendarEventCreate(
            title="Morning Sync",
            start_time="2026-11-25T10:00:00",
            duration_minutes=60,
        ))
        self.engine.create_event(CalendarEventCreate(
            title="Afternoon Sync",
            start_time="2026-11-25T14:00:00",
            duration_minutes=60,
        ))

        conn = get_db_connection(self._tmp_path)
        try:
            slots = find_free_time_slots(
                conn=conn,
                target_date_iso="2026-11-25",
                work_start_hour=9,
                work_end_hour=18,
                duration_minutes=60,
                timezone_id="Asia/Kolkata",
                max_suggestions=5,
            )
            # Available 60m slots should include 09:00-10:00, 11:00-12:00, 12:00-13:00, 13:00-14:00, 15:00-16:00
            self.assertGreater(len(slots), 0)
            for s in slots:
                # None of the slots can be between 10:00-11:00 or 14:00-15:00
                self.assertNotIn("10:00 AM - 11:00 AM", s["slot_label"])
                self.assertNotIn("02:00 PM - 03:00 PM", s["slot_label"])
        finally:
            conn.close()

    def test_03_alternative_slot_suggestions(self):
        # Fill 10:00 to 11:00
        self.engine.create_event(CalendarEventCreate(
            title="Blocker",
            start_time="2026-11-25T10:00:00",
            duration_minutes=60,
        ))

        conn = get_db_connection(self._tmp_path)
        try:
            target_dt = datetime(2026, 11, 25, 10, 0, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
            utc_ms, _ = convert_local_to_utc(target_dt, "Asia/Kolkata")

            alternatives = suggest_alternative_slots(
                conn=conn,
                requested_start_utc_ms=utc_ms,
                duration_minutes=45,
                timezone_id="Asia/Kolkata",
                max_suggestions=3,
            )
            self.assertGreater(len(alternatives), 0)
            self.assertLessEqual(len(alternatives), 3)
            # First alternative should be available in the 11:00 slot
            self.assertTrue(any("11:00" in a["slot_label"] or "09:00" in a["slot_label"] for a in alternatives))
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
