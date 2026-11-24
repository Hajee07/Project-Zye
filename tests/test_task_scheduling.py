"""
Day 29 Test Suite: Task Scheduling & Auto-Timeblocking Engine
Verifies priority validation, queue ordering, completion transitions,
and conflict-free calendar auto-timeblocking within working hours.
"""

from datetime import datetime
import os
import tempfile
import unittest
from pathlib import Path
import zoneinfo

from zye_personal_assistant.database import init_assistant_database, get_db_connection
from zye_personal_assistant.calendar_engine import CalendarEngine
from zye_personal_assistant.task_scheduler import TaskScheduler
from zye_personal_assistant.safety_gateway import SafetyGateway


class TestTaskScheduling(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_test_task_")
        os.close(self._tmp_fd)
        self.db_path = Path(self._tmp_path)
        init_assistant_database(self.db_path)
        self.safety = SafetyGateway(db_path=self.db_path)
        self.scheduler = TaskScheduler(db_path=self.db_path, safety_gateway=self.safety)
        self.calendar = CalendarEngine(db_path=self.db_path, safety_gateway=self.safety)

    def tearDown(self):
        try:
            self.db_path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_add_task_priority_validation(self):
        """Invalid priorities must be rejected with TASK_INVALID_PRIORITY."""
        res = self.scheduler.add_task(title="Invalid Priority Task", priority="SUPER_URGENT")
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res.get("error_code"), "TASK_INVALID_PRIORITY")

    def test_02_add_and_list_tasks(self):
        """Tasks are created and listed ordered by priority (CRITICAL > HIGH > MEDIUM > LOW)."""
        r1 = self.scheduler.add_task(title="Medium Task", priority="MEDIUM")
        r2 = self.scheduler.add_task(title="Critical Task", priority="CRITICAL")
        r3 = self.scheduler.add_task(title="Low Task", priority="LOW")

        self.assertEqual(r1["status"], "SUCCESS")
        self.assertEqual(r2["status"], "SUCCESS")
        self.assertEqual(r3["status"], "SUCCESS")

        tasks = self.scheduler.list_tasks(status="PENDING")
        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[0]["priority"], "CRITICAL")
        self.assertEqual(tasks[0]["title"], "Critical Task")

    def test_03_complete_task_lifecycle(self):
        """Marking task complete updates status and prevents double completion."""
        res = self.scheduler.add_task(title="Finish Documentation", priority="HIGH")
        task_id = res["task_id"]

        comp1 = self.scheduler.complete_task(task_id=task_id)
        self.assertEqual(comp1["status"], "SUCCESS")
        self.assertEqual(comp1["task_status"], "COMPLETED")

        comp2 = self.scheduler.complete_task(task_id=task_id)
        self.assertEqual(comp2["status"], "TASK_ALREADY_COMPLETED")

        comp3 = self.scheduler.complete_task(task_id=99999)
        self.assertIn(comp3["status"], ("NOT_FOUND", "TASK_NOT_FOUND"))

    def test_04_auto_timeblock_today_scheduling(self):
        """
        Auto-timeblock creates focus events in the calendar for pending tasks
        without overlapping existing meetings.
        """
        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        now = datetime.now(tz)
        target_date = now.strftime("%Y-%m-%d")

        # Add an existing calendar meeting from 10:00 to 11:00
        m_start = f"{target_date}T10:00:00+05:30"
        m_end = f"{target_date}T11:00:00+05:30"
        self.calendar.add_event(title="Team Standup", start_iso=m_start, end_iso=m_end)

        # Add two tasks
        t1 = self.scheduler.add_task(title="Code Review", priority="HIGH", est_minutes=30)
        t2 = self.scheduler.add_task(title="Write Unit Tests", priority="CRITICAL", est_minutes=45)

        res = self.scheduler.auto_timeblock_today(target_date_iso=target_date)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertGreaterEqual(res["scheduled_count"], 1)
        scheduled_tasks = res["scheduled_tasks"]

        for st in scheduled_tasks:
            start_str = st["scheduled_start_iso"]
            end_str = st["scheduled_end_iso"]
            self.assertTrue(bool(start_str))
            self.assertTrue(bool(end_str))

            cand_start = datetime.fromisoformat(start_str)
            cand_end = datetime.fromisoformat(end_str)
            ev_start = datetime.fromisoformat(m_start)
            ev_end = datetime.fromisoformat(m_end)

            overlap = (cand_start < ev_end) and (cand_end > ev_start)
            self.assertFalse(overlap, f"Focus block {start_str} - {end_str} overlaps with meeting {m_start} - {m_end}")

    def test_05_auto_timeblock_idempotency(self):
        """Running auto_timeblock twice does not duplicate focus blocks for already scheduled tasks."""
        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        now = datetime.now(tz)
        target_date = now.strftime("%Y-%m-%d")

        t1 = self.scheduler.add_task(title="Deploy Release", priority="CRITICAL", est_minutes=30)
        res1 = self.scheduler.auto_timeblock_today(target_date_iso=target_date)
        self.assertEqual(res1["scheduled_count"], 1)

        res2 = self.scheduler.auto_timeblock_today(target_date_iso=target_date)
        self.assertEqual(res2["scheduled_count"], 0)
        self.assertIn("No unscheduled pending tasks", res2["message"])


if __name__ == "__main__":
    unittest.main()
