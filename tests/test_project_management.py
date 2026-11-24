"""
Day 29 Test Suite: Project Management Engine
Verifies project CRUD, partial updates, blocker registration with risk transitions,
and dynamic completion percentage calculation from linked tasks.
"""

import os
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.database import init_assistant_database, get_db_connection
from zye_personal_assistant.project_manager import ProjectManager
from zye_personal_assistant.task_scheduler import TaskScheduler
from zye_personal_assistant.safety_gateway import SafetyGateway


class TestProjectManagement(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_test_proj_")
        os.close(self._tmp_fd)
        self.db_path = Path(self._tmp_path)
        init_assistant_database(self.db_path)
        self.safety = SafetyGateway(db_path=self.db_path)
        self.proj_manager = ProjectManager(db_path=self.db_path, safety_gateway=self.safety)
        self.scheduler = TaskScheduler(db_path=self.db_path, safety_gateway=self.safety)

    def tearDown(self):
        try:
            self.db_path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_create_and_update_project(self):
        """Creates a project and performs partial update preserving non-empty existing values."""
        res1 = self.proj_manager.create_or_update_project(
            name="Project Orion",
            objective="Deploy autonomous agent framework",
            deadline_iso="2026-12-31T23:59:59Z",
            status="ACTIVE",
        )
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertEqual(res1["action"], "CREATED")
        self.assertEqual(res1["name"], "Project Orion")
        self.assertEqual(res1["project_status"], "ACTIVE")

        # Partial update: update status without wiping objective
        res2 = self.proj_manager.create_or_update_project(
            name="Project Orion",
            status="ON_HOLD",
        )
        self.assertEqual(res2["status"], "SUCCESS")
        self.assertEqual(res2["action"], "UPDATED")
        self.assertEqual(res2["project_status"], "ON_HOLD")
        self.assertEqual(res2["objective"], "Deploy autonomous agent framework")

    def test_02_flag_blocker_lifecycle(self):
        """Flagging blockers updates status to AT_RISK or BLOCKED and raises risk level."""
        self.proj_manager.create_or_update_project(name="Project Apollo", status="ACTIVE")

        # Flag first blocker
        res1 = self.proj_manager.flag_blocker(name="Project Apollo", blocker_description="Pending API access")
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertEqual(res1["project_status"], "AT_RISK")
        self.assertEqual(res1["risk_level"], "HIGH")
        self.assertIn("Pending API access", res1["blockers"])

        # Flag second blocker with critical block
        res2 = self.proj_manager.flag_blocker(
            name="Project Apollo",
            blocker_description="Hardware failure",
            mark_blocked=True,
        )
        self.assertEqual(res2["status"], "SUCCESS")
        self.assertEqual(res2["project_status"], "BLOCKED")
        self.assertEqual(res2["risk_level"], "CRITICAL")
        self.assertEqual("Pending API access; Hardware failure", res2["blockers"])

    def test_03_flag_blocker_nonexistent_project(self):
        """Flagging blocker on non-existent project returns NOT_FOUND."""
        res = self.proj_manager.flag_blocker(name="Ghost Project", blocker_description="Missing repo")
        self.assertEqual(res["status"], "NOT_FOUND")
        self.assertEqual(res.get("error_code"), "PROJECT_NOT_FOUND")

    def test_04_status_board_dynamic_task_calculation(self):
        """Status board calculates completion_percent strictly from linked tasks in tasks table."""
        proj_name = "Agentic Upgrade"
        self.proj_manager.create_or_update_project(name=proj_name, objective="Core Day 29 upgrade")

        # Add 4 tasks: 2 completed, 2 pending
        t1 = self.scheduler.add_task(title="Task 1", project_name=proj_name)
        t2 = self.scheduler.add_task(title="Task 2", project_name=proj_name)
        t3 = self.scheduler.add_task(title="Task 3", project_name=proj_name)
        t4 = self.scheduler.add_task(title="Task 4", project_name=proj_name)

        self.scheduler.complete_task(task_id=t1["task_id"])
        self.scheduler.complete_task(task_id=t2["task_id"])

        board = self.proj_manager.get_status_board()
        self.assertEqual(board["status"], "SUCCESS")
        self.assertGreaterEqual(board["total_projects"], 1)

        proj = next(p for p in board["projects"] if p["name"] == proj_name)
        self.assertEqual(proj["total_tasks"], 4)
        self.assertEqual(proj["completed_tasks"], 2)
        self.assertEqual(proj["pending_tasks"], 2)
        self.assertEqual(proj["completion_percent"], 50.0)

        # Complete another task (3 of 4 = 75.0%)
        self.scheduler.complete_task(task_id=t3["task_id"])
        board2 = self.proj_manager.get_status_board()
        proj2 = next(p for p in board2["projects"] if p["name"] == proj_name)
        self.assertEqual(proj2["completed_tasks"], 3)
        self.assertEqual(proj2["completion_percent"], 75.0)


if __name__ == "__main__":
    unittest.main()
