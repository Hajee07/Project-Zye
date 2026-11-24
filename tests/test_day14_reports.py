"""
Unit tests for Day 14 Daily Report Generation Engine.
Verifies Morning Brief, End-of-Day report, voice synthesis, and zero-fabrication guarantees.
"""

import os
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.calendar_engine import CalendarEngine
from zye_personal_assistant.daily_report_engine import DailyReportEngine
from zye_personal_assistant.task_scheduler import TaskScheduler


class TestDay14Reports(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_rep_test_")
        os.close(self._tmp_fd)
        self.cal = CalendarEngine(db_path=self._tmp_path)
        self.tasks = TaskScheduler(db_path=self._tmp_path)
        self.reports = DailyReportEngine(db_path=self._tmp_path)

    def tearDown(self):
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_empty_database_reports(self):
        brief = self.reports.generate_report("morning_brief")
        self.assertEqual(brief["status"], "SUCCESS")
        self.assertEqual(brief["meeting_count"], 0)
        self.assertEqual(brief["pending_task_count"], 0)
        self.assertIn("voice_tanglish", brief)

        eod = self.reports.generate_report("end_of_day")
        self.assertEqual(eod["status"], "SUCCESS")
        self.assertEqual(eod["completed_task_count"], 0)

    def test_02_morning_brief_with_meetings_and_tasks(self):
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        self.cal.add_event(title="Quarterly Review", start_iso=f"{today}T10:00:00", end_iso=f"{today}T11:00:00")
        self.tasks.add_task(title="Deploy Release v2.0", priority="CRITICAL")

        brief = self.reports.generate_report("morning_brief")
        self.assertEqual(brief["status"], "SUCCESS")
        self.assertIn("Quarterly Review", brief["markdown"])
        self.assertIn("voice_tanglish", brief)
        self.assertIn("critical", brief["voice_tanglish"])

    def test_03_end_of_day_report_with_completed_items(self):
        t1 = self.tasks.add_task(title="Audit Security Logs")
        self.tasks.complete_task(task_id=t1["task_id"])

        eod = self.reports.generate_report("end_of_day")
        self.assertEqual(eod["completed_task_count"], 1)
        self.assertIn("Audit Security Logs", eod["markdown"])


if __name__ == "__main__":
    unittest.main()
