"""
Unit tests for Day 14 Meeting Reminder Engine.
Verifies 15-minute and 2-minute proactive reminders, duplicate prevention, and Tanglish strings.
"""

import inspect
import os
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.calendar_engine import CalendarEngine
from zye_personal_assistant.reminder_engine import ReminderEngine, assistant_reminder_daemon


class TestDay14Reminders(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_rem_test_")
        os.close(self._tmp_fd)
        self.cal = CalendarEngine(db_path=self._tmp_path)
        self.rem = ReminderEngine(db_path=self._tmp_path)

    def tearDown(self):
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_fifteen_minute_reminder_triggered(self):
        # Event starts in 14 minutes from 10:00:00 (i.e. 10:14:00)
        self.cal.add_event(title="Sprint Planning", start_iso="2026-11-20T10:14:00", end_iso="2026-11-20T11:00:00")
        alerts = self.rem.check_meeting_reminders(reference_time_iso="2026-11-20T10:00:00")
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["reminder_type"], "15_MINUTE")
        self.assertIn("15 minutes", alerts[0]["message_en"])
        self.assertIn("15 minutes-la start aagum", alerts[0]["message_tanglish"])

    def test_02_two_minute_reminder_triggered(self):
        # Event starts in 1.5 minutes from 10:00:00 (i.e. 10:01:30)
        self.cal.add_event(title="Client Sync", start_iso="2026-11-20T10:01:30", end_iso="2026-11-20T10:30:00")
        alerts = self.rem.check_meeting_reminders(reference_time_iso="2026-11-20T10:00:00")
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["reminder_type"], "2_MINUTE")
        self.assertIn("2 minutes", alerts[0]["message_en"])
        self.assertIn("2 minutes-la start aagum", alerts[0]["message_tanglish"])

    def test_03_duplicate_reminders_prevented(self):
        self.cal.add_event(title="Budget Review", start_iso="2026-11-20T10:12:00", end_iso="2026-11-20T11:00:00")
        # First scan triggers alert
        alerts1 = self.rem.check_meeting_reminders(reference_time_iso="2026-11-20T10:00:00")
        self.assertEqual(len(alerts1), 1)

        # Second immediate scan on same reference time must NOT generate duplicate alert
        alerts2 = self.rem.check_meeting_reminders(reference_time_iso="2026-11-20T10:00:00")
        self.assertEqual(len(alerts2), 0, "Duplicate reminders must be prevented")

    def test_04_daemon_coroutine_signature(self):
        self.assertTrue(
            inspect.iscoroutinefunction(assistant_reminder_daemon),
            "assistant_reminder_daemon must be an async coroutine function"
        )


if __name__ == "__main__":
    unittest.main()
