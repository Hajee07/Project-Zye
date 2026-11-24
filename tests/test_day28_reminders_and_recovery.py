"""
Unit and integration tests for Day 28 Persistent Reminders & Recovery Engine.
Tests 15m/2m reminder generation, status state machine (PENDING -> CLAIMED -> DELIVERED/FAILED),
late-booking suppression, and startup crash recovery reconciliation.
"""

import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from zye_personal_assistant.calendar.calendar_database import initialize_calendar_database, get_db_connection
from zye_personal_assistant.calendar.calendar_event_engine import CalendarEventEngine
from zye_personal_assistant.calendar.calendar_models import CalendarEventCreate
from zye_personal_assistant.reminders.reminder_models import ReminderStatus, ReminderType
from zye_personal_assistant.reminders.reminder_recovery import reconcile_reminders_on_startup
from zye_personal_assistant.reminders.reminder_repository import (
    create_reminders_for_event,
    get_due_reminders,
    claim_reminder,
    mark_reminder_delivered,
    mark_reminder_failed,
    cancel_reminders_for_event,
)


class TestDay28RemindersAndRecovery(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_d28_rem_")
        os.close(self._tmp_fd)
        initialize_calendar_database(self._tmp_path)
        self.engine = CalendarEventEngine(db_path=self._tmp_path, default_tz="Asia/Kolkata")

    def tearDown(self):
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_reminders_created_in_pending_state(self):
        # Event in the future (2 hours ahead)
        future_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        res = self.engine.create_event(CalendarEventCreate(
            title="Future Discussion",
            start_time=future_time,
            duration_minutes=30,
        ))
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(len(res.reminders), 2)

        conn = get_db_connection(self._tmp_path)
        try:
            rows = conn.execute("SELECT reminder_type, status FROM event_reminders WHERE event_id = ?;", (res.event_id,)).fetchall()
            self.assertEqual(len(rows), 2)
            types_statuses = {r["reminder_type"]: r["status"] for r in rows}
            self.assertEqual(types_statuses["15_MIN"], "PENDING")
            self.assertEqual(types_statuses["2_MIN"], "PENDING")
        finally:
            conn.close()

    def test_02_late_creation_suppression_under_15_mins(self):
        conn = get_db_connection(self._tmp_path)
        try:
            now_ms = int(time.time() * 1000)
            # Starts in 10 minutes (600,000 ms)
            start_ms = now_ms + (10 * 60 * 1000)

            conn.execute("""
                INSERT INTO events (id, title, start_iso, end_iso, start_utc, end_utc, created_at)
                VALUES (99, 'Short Notice Call', '2026-11-20T10:00:00', '2026-11-20T11:00:00', ?, ?, '2026-11-20T09:00:00');
            """, (start_ms, start_ms + 3600000))
            conn.commit()

            reminders = create_reminders_for_event(
                conn=conn,
                event_id=99,
                event_version=1,
                start_utc_ms=start_ms,
                created_at_utc_ms=now_ms,
            )
            self.assertEqual(len(reminders), 2)
            types_statuses = {r["reminder_type"]: r["status"] for r in reminders}
            # 15m is suppressed because <15m remain, 2m is pending
            self.assertEqual(types_statuses["15_MIN"], "SUPPRESSED")
            self.assertEqual(types_statuses["2_MIN"], "PENDING")
        finally:
            conn.close()

    def test_03_claim_and_deliver_lifecycle(self):
        conn = get_db_connection(self._tmp_path)
        try:
            now_ms = int(time.time() * 1000)
            # Starts in 5 minutes (trigger for 15m was in the past)
            start_ms = now_ms + (5 * 60 * 1000)

            conn.execute("""
                INSERT INTO events (id, title, start_iso, end_iso, start_utc, end_utc, created_at)
                VALUES (101, 'Quick Checkin', '2026-11-20T10:00:00', '2026-11-20T10:30:00', ?, ?, '2026-11-20T09:00:00');
            """, (start_ms, start_ms + 1800000))

            # Manually insert a PENDING reminder due now
            conn.execute("""
                INSERT INTO event_reminders (event_id, event_version, reminder_type, offset_seconds, due_at_utc, status, created_at_utc)
                VALUES (101, 1, '15_MIN', 900, ?, 'PENDING', ?);
            """, (now_ms - 1000, now_ms))
            conn.commit()

            # 1. Query due reminders
            due = get_due_reminders(conn, as_of_utc_ms=now_ms)
            self.assertEqual(len(due), 1)
            rem_id = due[0]["id"]

            # 2. Claim reminder
            claimed = claim_reminder(conn, rem_id, claimed_at_utc_ms=now_ms)
            self.assertTrue(claimed)

            # Verify status is CLAIMED
            row = conn.execute("SELECT status FROM event_reminders WHERE id = ?;", (rem_id,)).fetchone()
            self.assertEqual(row["status"], "CLAIMED")

            # 3. Mark delivered
            delivered = mark_reminder_delivered(conn, rem_id, delivered_at_utc_ms=now_ms + 100)
            self.assertTrue(delivered)

            # Verify status is DELIVERED
            row = conn.execute("SELECT status FROM event_reminders WHERE id = ?;", (rem_id,)).fetchone()
            self.assertEqual(row["status"], "DELIVERED")
        finally:
            conn.close()

    def test_04_startup_reconciliation_reclaims_stale_and_suppresses_expired(self):
        conn = get_db_connection(self._tmp_path)
        try:
            now_ms = int(time.time() * 1000)

            # Insert an event that already started 10 minutes ago
            conn.execute("""
                INSERT INTO events (id, title, start_iso, end_iso, start_utc, end_utc, created_at)
                VALUES (201, 'Past Event', '2026-11-20T10:00:00', '2026-11-20T11:00:00', ?, ?, '2026-11-20T09:00:00');
            """, (now_ms - (10 * 60 * 1000), now_ms + (50 * 60 * 1000)))

            # Pending reminder for this past event
            conn.execute("""
                INSERT INTO event_reminders (event_id, event_version, reminder_type, offset_seconds, due_at_utc, status, created_at_utc)
                VALUES (201, 1, '15_MIN', 900, ?, 'PENDING', ?);
            """, (now_ms - (25 * 60 * 1000), now_ms - (30 * 60 * 1000)))

            # Insert an event in the future (in 30 mins) with a STALE CLAIM (>120s ago)
            conn.execute("""
                INSERT INTO events (id, title, start_iso, end_iso, start_utc, end_utc, created_at)
                VALUES (202, 'Future Event', '2026-11-20T12:00:00', '2026-11-20T13:00:00', ?, ?, '2026-11-20T10:00:00');
            """, (now_ms + (30 * 60 * 1000), now_ms + (90 * 60 * 1000)))

            conn.execute("""
                INSERT INTO event_reminders (event_id, event_version, reminder_type, offset_seconds, due_at_utc, status, claimed_at_utc, created_at_utc)
                VALUES (202, 1, '15_MIN', 900, ?, 'CLAIMED', ?, ?);
            """, (now_ms + (15 * 60 * 1000), now_ms - 200000, now_ms - 300000))

            conn.commit()
        finally:
            conn.close()

        # Run startup reconciliation
        stats = reconcile_reminders_on_startup(self._tmp_path)
        self.assertEqual(stats["reclaimed_stale_claims"], 1)
        self.assertEqual(stats["suppressed_expired_reminders"], 1)

        conn = get_db_connection(self._tmp_path)
        try:
            # Event 201 reminder must be SUPPRESSED
            row1 = conn.execute("SELECT status FROM event_reminders WHERE event_id = 201;").fetchone()
            self.assertEqual(row1["status"], "SUPPRESSED")

            # Event 202 reminder must be PENDING again
            row2 = conn.execute("SELECT status FROM event_reminders WHERE event_id = 202;").fetchone()
            self.assertEqual(row2["status"], "PENDING")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
