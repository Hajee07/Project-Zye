"""
Unit and integration tests for Day 28 Smart Calendar Database & Migrations.
Tests SQLite schema versioning, backward-compatible table migration, indices,
and BEGIN IMMEDIATE atomic transactional integrity.
"""

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.calendar.calendar_database import (
    initialize_calendar_database,
    atomic_calendar_transaction,
    get_schema_version,
    set_schema_version,
    get_db_connection,
)


class TestDay28CalendarDatabase(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_d28_db_")
        os.close(self._tmp_fd)

    def tearDown(self):
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_fresh_initialization_creates_schema_v28(self):
        initialize_calendar_database(self._tmp_path)
        ver = get_schema_version(self._tmp_path)
        self.assertEqual(ver, 28)

        conn = get_db_connection(self._tmp_path)
        try:
            # Verify events columns
            columns = [col[1] for col in conn.execute("PRAGMA table_info(events);").fetchall()]
            for expected in ["id", "title", "start_iso", "end_iso", "start_utc", "end_utc", "timezone_id", "version", "source", "operation_id", "reminded_15m", "reminded_2m"]:
                self.assertIn(expected, columns)

            # Verify event_reminders columns
            rem_columns = [col[1] for col in conn.execute("PRAGMA table_info(event_reminders);").fetchall()]
            for expected in ["id", "event_id", "event_version", "reminder_type", "due_at_utc", "status", "created_at_utc"]:
                self.assertIn(expected, rem_columns)

            # Verify indices
            indices = [idx[1] for idx in conn.execute("SELECT * FROM sqlite_master WHERE type = 'index';").fetchall()]
            self.assertIn("idx_events_start_utc", indices)
            self.assertIn("idx_events_end_utc", indices)
            self.assertIn("idx_reminders_due", indices)
        finally:
            conn.close()

    def test_02_migration_from_legacy_schema(self):
        # Simulate legacy Day 14 events table
        conn = sqlite3.connect(self._tmp_path)
        conn.execute("""
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_iso TEXT NOT NULL,
                end_iso TEXT NOT NULL,
                location TEXT DEFAULT 'online',
                notes TEXT DEFAULT '',
                reminded_15m INTEGER DEFAULT 0,
                reminded_2m INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
        """)
        conn.execute("""
            INSERT INTO events (title, start_iso, end_iso, created_at)
            VALUES ('Legacy Meeting', '2026-11-20T10:00:00', '2026-11-20T11:00:00', '2026-11-19T10:00:00');
        """)
        conn.commit()
        conn.close()

        # Run Day 28 migration
        initialize_calendar_database(self._tmp_path)
        ver = get_schema_version(self._tmp_path)
        self.assertEqual(ver, 28)

        conn = get_db_connection(self._tmp_path)
        try:
            row = conn.execute("SELECT * FROM events WHERE id = 1;").fetchone()
            self.assertEqual(row["title"], "Legacy Meeting")
            self.assertEqual(row["version"], 1)
            self.assertIsNotNone(row["start_utc"])
            self.assertGreater(row["start_utc"], 0)
        finally:
            conn.close()

    def test_03_atomic_calendar_transaction_rollback_on_error(self):
        initialize_calendar_database(self._tmp_path)

        with self.assertRaises(RuntimeError):
            with atomic_calendar_transaction(self._tmp_path) as conn:
                conn.execute(
                    "INSERT INTO events (title, start_iso, end_iso, created_at) VALUES ('Rollback Event', '2026-11-25T10:00:00', '2026-11-25T11:00:00', '2026-11-21T10:00:00');"
                )
                raise RuntimeError("Forced test exception")

        conn = get_db_connection(self._tmp_path)
        try:
            count = conn.execute("SELECT COUNT(*) FROM events WHERE title = 'Rollback Event';").fetchone()[0]
            self.assertEqual(count, 0, "Event must be rolled back on exception")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
