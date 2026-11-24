"""
Unit tests for Day 14 Project Management Support Engine.
Verifies project CRUD, blocker tracking, delay risk calculation, and status board.
"""

import os
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.project_manager import ProjectManager
from zye_personal_assistant.task_scheduler import TaskScheduler


class TestDay14Projects(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_prj_test_")
        os.close(self._tmp_fd)
        self.pm = ProjectManager(db_path=self._tmp_path)
        self.tasks = TaskScheduler(db_path=self._tmp_path)

    def tearDown(self):
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_create_or_update_project(self):
        res1 = self.pm.create_or_update_project(name="Zye Day 14", objective="Personal Assistant Core", deadline_iso="2026-11-25")
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertEqual(res1["action"], "CREATED")

        res2 = self.pm.create_or_update_project(name="Zye Day 14", objective="Updated: 10 Subsystems")
        self.assertEqual(res2["status"], "SUCCESS")
        self.assertEqual(res2["action"], "UPDATED")

    def test_02_flag_blocker_marks_at_risk(self):
        self.pm.create_or_update_project(name="Telemetry Pipeline")
        flag_res = self.pm.flag_blocker(name="Telemetry Pipeline", blocker_description="Awaiting GPU hardware access")
        self.assertEqual(flag_res["status"], "SUCCESS")
        self.assertEqual(flag_res["project_status"], "AT_RISK")
        self.assertIn("Awaiting GPU", flag_res["blockers"])

    def test_03_status_board_with_tasks_and_delay_risk(self):
        self.pm.create_or_update_project(name="Core Assistant")
        self.tasks.add_task(title="Build Task Scheduler", project_name="Core Assistant", priority="CRITICAL")
        self.tasks.add_task(title="Build Email Engine", project_name="Core Assistant", priority="MEDIUM")

        sb = self.pm.get_status_board()
        self.assertEqual(sb["total_projects"], 1)
        proj = sb["projects"][0]
        self.assertEqual(proj["total_tasks"], 2)
        self.assertEqual(proj["critical_tasks"], 1)
        # Critical tasks pending without blockers -> MEDIUM delay risk
        self.assertEqual(proj["delay_risk"], "MEDIUM")


if __name__ == "__main__":
    unittest.main()
