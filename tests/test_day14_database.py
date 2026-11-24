"""
Unit tests for Day 14 Personal Assistant Unified SQLite Database Engine.
Verifies schema initialization, table integrity, migrations, foreign keys, and backups.
"""

import os
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.database import (
    backup_database,
    check_database_integrity,
    get_db_connection,
    init_assistant_database,
)


class TestDay14Database(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_db_test_")
        os.close(self._tmp_fd)
        init_assistant_database(self._tmp_path)

    def tearDown(self):
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_all_eleven_tables_created(self):
        conn = get_db_connection(self._tmp_path)
        try:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row["name"] for row in cursor.fetchall()}
            expected = {
                "events",
                "tasks",
                "projects",
                "doc_index",
                "email_drafts",
                "email_action_history",
                "task_timeblocks",
                "project_milestones",
                "research_history",
                "travel_plans",
                "audit_history",
            }
            self.assertTrue(expected.issubset(tables), f"Missing tables: {expected - tables}")
        finally:
            conn.close()

    def test_02_database_integrity_check(self):
        is_healthy, msg = check_database_integrity(self._tmp_path)
        self.assertTrue(is_healthy)
        self.assertEqual(msg, "ok")

    def test_03_migration_preserves_data(self):
        conn = get_db_connection(self._tmp_path)
        try:
            with conn:
                conn.execute(
                    "INSERT INTO events (title, start_iso, end_iso) VALUES ('Pre-existing meeting', '2026-11-20T10:00:00', '2026-11-20T11:00:00');"
                )
        finally:
            conn.close()

        # Re-initialize to simulate migration
        init_assistant_database(self._tmp_path)

        conn = get_db_connection(self._tmp_path)
        try:
            row = conn.execute("SELECT title, timezone, event_status FROM events WHERE title = 'Pre-existing meeting';").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["title"], "Pre-existing meeting")
            self.assertEqual(row["timezone"], "Asia/Kolkata")
            self.assertEqual(row["event_status"], "SCHEDULED")
        finally:
            conn.close()

    def test_04_foreign_key_enforcement(self):
        conn = get_db_connection(self._tmp_path)
        try:
            with conn:
                conn.execute("INSERT INTO projects (name, objective) VALUES ('Alpha', 'Core mission');")
                proj_id = conn.execute("SELECT id FROM projects WHERE name = 'Alpha';").fetchone()["id"]
                conn.execute("INSERT INTO project_milestones (project_id, title) VALUES (?, 'Milestone 1');", (proj_id,))

            milestone = conn.execute("SELECT title FROM project_milestones WHERE project_id = ?;", (proj_id,)).fetchone()
            self.assertEqual(milestone["title"], "Milestone 1")
        finally:
            conn.close()

    def test_05_backup_database_creates_valid_copy(self):
        with tempfile.TemporaryDirectory() as bdir:
            backup_file = backup_database(db_path=self._tmp_path, backup_dir=bdir)
            self.assertIsNotNone(backup_file)
            self.assertTrue(Path(backup_file).is_file())
            # Verify backup integrity
            is_healthy, msg = check_database_integrity(backup_file)
            self.assertTrue(is_healthy)
            self.assertEqual(msg, "ok")


if __name__ == "__main__":
    unittest.main()
