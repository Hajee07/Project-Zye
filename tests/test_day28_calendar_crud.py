"""
Unit and integration tests for Day 28 Calendar CRUD Operations.
Tests event creation, reading, updating, rescheduling, soft-cancellation,
hard-deletion, and operation_id idempotency.
"""

import os
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.calendar.calendar_database import initialize_calendar_database
from zye_personal_assistant.calendar.calendar_event_engine import CalendarEventEngine
from zye_personal_assistant.calendar.calendar_models import CalendarEventCreate, CalendarEventUpdate


class TestDay28CalendarCRUD(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_d28_crud_")
        os.close(self._tmp_fd)
        initialize_calendar_database(self._tmp_path)
        self.engine = CalendarEventEngine(db_path=self._tmp_path, default_tz="Asia/Kolkata")

    def tearDown(self):
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_create_event_with_default_duration(self):
        payload = CalendarEventCreate(
            title="Design Review",
            start_time="2026-11-25T10:00:00",
            location="Room 404",
        )
        res = self.engine.create_event(payload)
        self.assertEqual(res.status, "SUCCESS")
        self.assertIsNotNone(res.event_id)
        self.assertEqual(res.title, "Design Review")
        self.assertIn("11:00:00", res.end_iso)
        self.assertEqual(len(res.reminders), 2)

    def test_02_get_event(self):
        payload = CalendarEventCreate(
            title="All Hands",
            start_time="2026-11-25T11:00:00",
            duration_minutes=30,
        )
        res = self.engine.create_event(payload)
        ev = self.engine.get_event(res.event_id)
        self.assertIsNotNone(ev)
        self.assertEqual(ev.title, "All Hands")
        self.assertEqual(ev.version, 1)
        self.assertEqual(ev.event_status, "SCHEDULED")

    def test_03_update_event_metadata_only(self):
        res = self.engine.create_event(CalendarEventCreate(
            title="Draft Meeting",
            start_time="2026-11-25T14:00:00",
        ))
        update_payload = CalendarEventUpdate(
            event_id=res.event_id,
            title="Final Review",
            notes="Bring slides",
        )
        res_update = self.engine.update_event(update_payload)
        self.assertEqual(res_update.status, "SUCCESS")
        self.assertEqual(res_update.title, "Final Review")

        ev = self.engine.get_event(res.event_id)
        self.assertEqual(ev.title, "Final Review")
        self.assertEqual(ev.notes, "Bring slides")
        self.assertEqual(ev.version, 2)

    def test_04_reschedule_event_updates_time_and_refreshes_reminders(self):
        res = self.engine.create_event(CalendarEventCreate(
            title="Tech Sync",
            start_time="2026-11-25T15:00:00",
            duration_minutes=45,
        ))
        res_reschedule = self.engine.reschedule_event(
            event_id=res.event_id,
            new_start_time="2026-11-25T16:00:00",
            new_duration_minutes=60,
        )
        self.assertEqual(res_reschedule.status, "SUCCESS")
        self.assertIn("16:00:00", res_reschedule.start_iso)
        self.assertIn("17:00:00", res_reschedule.end_iso)
        self.assertEqual(len(res_reschedule.reminders), 2)

        ev = self.engine.get_event(res.event_id)
        self.assertEqual(ev.version, 2)

    def test_05_soft_cancel_event(self):
        res = self.engine.create_event(CalendarEventCreate(
            title="Client Pitch",
            start_time="2026-11-25T18:00:00",
        ))
        cancel_res = self.engine.cancel_event(res.event_id)
        self.assertEqual(cancel_res.status, "CANCELLED")

        ev = self.engine.get_event(res.event_id)
        self.assertEqual(ev.event_status, "CANCELLED")

        # Modifying a cancelled event should be rejected
        res_update = self.engine.update_event(CalendarEventUpdate(
            event_id=res.event_id,
            title="Revived Pitch",
        ))
        self.assertEqual(res_update.status, "ERROR")
        self.assertEqual(res_update.error_code, "CALENDAR_EVENT_CANCELLED")

    def test_06_delete_event_requires_confirmation(self):
        res = self.engine.create_event(CalendarEventCreate(
            title="Temp Sync",
            start_time="2026-11-25T19:00:00",
        ))
        # Without confirmation
        del_fail = self.engine.delete_event(res.event_id, confirmed=False)
        self.assertEqual(del_fail.status, "ERROR")
        self.assertEqual(del_fail.error_code, "CONFIRMATION_REQUIRED")

        # With confirmation
        del_ok = self.engine.delete_event(res.event_id, confirmed=True)
        self.assertIn(del_ok.status, ["SUCCESS", "DELETED"])
        self.assertIsNone(self.engine.get_event(res.event_id))

    def test_07_operation_id_idempotency(self):
        op_id = "op-unique-uuid-999"
        res1 = self.engine.create_event(CalendarEventCreate(
            title="Idempotent Call",
            start_time="2026-11-25T20:00:00",
            operation_id=op_id,
        ))
        self.assertEqual(res1.status, "SUCCESS")

        # Second creation with identical operation_id must return existing event
        res2 = self.engine.create_event(CalendarEventCreate(
            title="Idempotent Call",
            start_time="2026-11-25T20:00:00",
            operation_id=op_id,
        ))
        self.assertEqual(res2.status, "SUCCESS")
        self.assertEqual(res2.event_id, res1.event_id)
        self.assertIn("already scheduled", res2.message)


if __name__ == "__main__":
    unittest.main()
