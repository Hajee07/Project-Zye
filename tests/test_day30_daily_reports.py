"""
Day 30 Test Suite: Daily Executive Briefing & End-of-Day Reporting Engine
Tests Morning Briefs, End-of-Day reports, meeting timelines, task priorities,
overdue task detection, project blocker summaries, and voice outputs.
"""

from datetime import datetime, timezone
import os
import tempfile
import unittest
from pathlib import Path
import zoneinfo

from zye_personal_assistant.database import init_assistant_database, get_db_connection
from zye_personal_assistant.calendar_engine import CalendarEngine
from zye_personal_assistant.task_scheduler import TaskScheduler
from zye_personal_assistant.project_manager import ProjectManager
from zye_personal_assistant.daily_report_engine import DailyReportEngine


class TestDay30DailyReports(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_test_reports_")
        os.close(self._tmp_fd)
        self.db_path = Path(self._tmp_path)
        init_assistant_database(self.db_path)
        self.engine = DailyReportEngine(db_path=self.db_path, default_timezone="Asia/Kolkata")
        self.calendar = CalendarEngine(db_path=self.db_path)
        self.scheduler = TaskScheduler(db_path=self.db_path)
        self.projects = ProjectManager(db_path=self.db_path)

    def tearDown(self):
        try:
            self.db_path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_morning_brief_with_meetings_and_tasks(self):
        """Generates structured Morning Brief with today's meetings and top priorities."""
        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        today_str = datetime.now(tz).strftime("%Y-%m-%d")

        # Add meeting
        self.calendar.add_event(
            title="Team Architecture Sync",
            start_iso=f"{today_str}T11:00:00+05:30",
            end_iso=f"{today_str}T12:00:00+05:30",
            location="Room Alpha",
        )

        # Add high priority task
        self.scheduler.add_task(title="Deploy Day 30 Engine", priority="CRITICAL", due_iso=today_str)
        # Add normal task
        self.scheduler.add_task(title="Refactor Helper Function", priority="LOW")

        res = self.engine.generate_report(report_type="morning_brief", include_email_summary=False)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["report_type"], "morning_brief")
        self.assertEqual(res["meeting_count"], 1)
        self.assertIsNotNone(res["next_meeting"])
        self.assertEqual(res["next_meeting"]["title"], "Team Architecture Sync")
        self.assertEqual(res["pending_task_count"], 2)
        self.assertEqual(res["critical_task_count"], 1)
        self.assertIn("Architecture Sync", res["markdown"])
        self.assertIn("Good morning", res["voice_tanglish"])
        self.assertIn("Good morning", res["voice_en"])

    def test_02_morning_brief_zero_events_honesty(self):
        """When no meetings exist, report states zero confirmed meetings without hallucination."""
        res = self.engine.generate_report(report_type="morning_brief", include_email_summary=False)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["meeting_count"], 0)
        self.assertIsNone(res["next_meeting"])
        self.assertIn("No confirmed meetings scheduled", res["markdown"])

    def test_03_overdue_tasks_detection(self):
        """Identifies pending tasks whose due date has passed as overdue."""
        past_date = "2026-01-01"
        self.scheduler.add_task(title="Old Unfinished Task", priority="HIGH", due_iso=past_date)

        res = self.engine.generate_report(report_type="morning_brief", include_email_summary=False)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertGreaterEqual(res["overdue_task_count"], 1)
        self.assertTrue(any("Old Unfinished Task" in t["title"] for t in res["overdue_tasks"]))

    def test_04_end_of_day_report(self):
        """End-of-Day report aggregates completed work, carryover items, and blockers."""
        t1 = self.scheduler.add_task(title="Fix CSS styling")
        t2 = self.scheduler.add_task(title="Write Unit Tests")
        self.scheduler.complete_task(task_id=t1["task_id"])

        self.projects.create_or_update_project(name="Platform Core", status="ACTIVE")
        self.projects.flag_blocker(name="Platform Core", blocker_description="Awaiting security audit")

        res = self.engine.generate_report(report_type="end_of_day", include_email_summary=False)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["report_type"], "end_of_day")
        self.assertEqual(res["completed_task_count"], 1)
        self.assertEqual(res["pending_task_count"], 1)
        self.assertIn("Fix CSS styling", res["markdown"])
        self.assertIn("Platform Core", res["markdown"])
        self.assertIn("end of day report", res["voice_tanglish"].lower())


if __name__ == "__main__":
    unittest.main()
