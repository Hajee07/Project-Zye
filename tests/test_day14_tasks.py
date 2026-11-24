"""
Unit tests for Day 14 Task Scheduling and Auto-Timeblocking Engine.
Verifies priority ordering, completion updates, and conflict-free calendar timeblocking.
"""

import os
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.calendar_engine import CalendarEngine
from zye_personal_assistant.project_manager import ProjectManager
from zye_personal_assistant.safety_gateway import SafetyGateway
from zye_personal_assistant.task_scheduler import TaskScheduler


class TestDay14Tasks(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_tsk_test_")
        os.close(self._tmp_fd)
        sg = SafetyGateway(db_path=self._tmp_path)
        self.cal = CalendarEngine(db_path=self._tmp_path, safety_gateway=sg)
        self.pm = ProjectManager(db_path=self._tmp_path, safety_gateway=sg)
        self.tasks = TaskScheduler(db_path=self._tmp_path, safety_gateway=sg)

    def tearDown(self):
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_add_task_and_priority_sorting(self):
        self.tasks.add_task(title="Refactor CSS", priority="LOW", due_iso="2026-11-25T18:00:00")
        self.tasks.add_task(title="Fix Prod Bug", priority="CRITICAL", due_iso="2026-11-21T12:00:00")
        self.tasks.add_task(title="Update Docs", priority="MEDIUM", due_iso="2026-11-22T10:00:00")

        task_list = self.tasks.list_tasks(status="PENDING")
        self.assertEqual(len(task_list), 3)
        self.assertEqual(task_list[0]["title"], "Fix Prod Bug")
        self.assertEqual(task_list[0]["priority"], "CRITICAL")
        self.assertEqual(task_list[1]["title"], "Update Docs")
        self.assertEqual(task_list[2]["title"], "Refactor CSS")

    def test_02_task_completion_updates_project_progress(self):
        self.pm.create_or_update_project(name="Platform Migration")
        t1 = self.tasks.add_task(title="DB Migration", project_name="Platform Migration")
        t2 = self.tasks.add_task(title="API Migration", project_name="Platform Migration")

        # Complete 1 of 2 tasks -> 50%
        res = self.tasks.complete_task(task_id=t1["task_id"])
        self.assertEqual(res["status"], "SUCCESS")

        sb = self.pm.get_status_board()
        proj = [p for p in sb["projects"] if p["name"] == "Platform Migration"][0]
        self.assertEqual(proj["completion_percent"], 50.0)

    def test_03_auto_timeblocking_preserves_meetings(self):
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        # Create an existing meeting today from 10:00 to 11:30
        self.cal.add_event(title="Client Sync", start_iso=f"{today}T10:00:00", end_iso=f"{today}T11:30:00")

        # Add two pending tasks
        self.tasks.add_task(title="Write Proposal", priority="HIGH", est_minutes=45)
        self.tasks.add_task(title="Review Code", priority="MEDIUM", est_minutes=30)

        # Trigger auto-timeblock
        block_res = self.tasks.auto_timeblock_today(buffer_minutes=10, work_start_hour=9, work_end_hour=17, target_date=today)
        self.assertEqual(block_res["status"], "SUCCESS")
        self.assertGreater(block_res["scheduled_count"], 0)

        # Verify no timeblocks overlap with the 10:00-11:30 meeting
        conflict_check = self.cal.check_conflicts(start_iso=f"{today}T10:00:00", end_iso=f"{today}T11:30:00")
        self.assertEqual(conflict_check["conflict_count"], 1, "Only the original meeting should exist in that window")


if __name__ == "__main__":
    unittest.main()
