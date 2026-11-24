"""
Offline-First SQLite Calendar Database & Migration Subsystem (Day 28).
Provides atomic transactions (BEGIN IMMEDIATE), foreign keys, schema versioning,
and persistent reminder tables while safely preserving legacy event data.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Optional, Tuple

from zye_personal_assistant.database import (
    _DB_LOCK,
    get_db_connection,
    get_default_db_path,
    backup_database,
    check_database_integrity,
)

logger = logging.getLogger("zye.personal_assistant.calendar.database")

SCHEMA_VERSION = 28  # Day 28 schema milestone


def get_schema_version(conn: sqlite3.Connection | str | Path | None = None) -> int:
    """Retrieve current calendar schema version."""
    close_after = False
    if conn is None or isinstance(conn, (str, Path)):
        conn = get_db_connection(conn)
        close_after = True
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_versions (
                module TEXT PRIMARY KEY,
                version INTEGER NOT NULL,
                updated_at TEXT DEFAULT (datetime('now'))
            );
        """)
        row = conn.execute("SELECT version FROM schema_versions WHERE module = 'calendar';").fetchone()
        return int(row["version"]) if row else 14  # Day 14 foundation
    except Exception as exc:
        logger.warning("Error fetching schema version: %s", exc)
        return 14
    finally:
        if close_after:
            conn.close()


def set_schema_version(conn: sqlite3.Connection | str | Path | None = None, version: int = SCHEMA_VERSION) -> None:
    """Record upgraded schema version."""
    close_after = False
    if conn is None or isinstance(conn, (str, Path)):
        conn = get_db_connection(conn)
        close_after = True
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_versions (
                module TEXT PRIMARY KEY,
                version INTEGER NOT NULL,
                updated_at TEXT DEFAULT (datetime('now'))
            );
        """)
        conn.execute("""
            INSERT INTO schema_versions (module, version, updated_at)
            VALUES ('calendar', ?, datetime('now'))
            ON CONFLICT(module) DO UPDATE SET version = excluded.version, updated_at = excluded.updated_at;
        """, (version,))
        if close_after:
            conn.commit()
    finally:
        if close_after:
            conn.close()


def initialize_calendar_database(db_path: str | Path | None = None) -> None:
    """
    Apply Day 28 schema upgrades and ensure all tables, columns, and indices exist.
    Preserves all existing records and backfills missing UTC epoch timestamps.
    """
    with _DB_LOCK:
        conn = get_db_connection(db_path)
        try:
            with conn:
                # 1. Ensure events table exists
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        start_iso TEXT NOT NULL,
                        end_iso TEXT NOT NULL,
                        location TEXT DEFAULT '',
                        notes TEXT DEFAULT '',
                        reminded_15m INTEGER DEFAULT 0,
                        reminded_2m INTEGER DEFAULT 0,
                        timezone TEXT DEFAULT 'Asia/Kolkata',
                        created_at TEXT DEFAULT (datetime('now')),
                        updated_at TEXT DEFAULT (datetime('now')),
                        event_status TEXT DEFAULT 'SCHEDULED',
                        reminder_state TEXT DEFAULT 'PENDING'
                    );
                """)

                # 2. Add Day 28 columns to events table if missing
                cursor = conn.execute("PRAGMA table_info(events);")
                existing_cols = {row["name"] for row in cursor.fetchall()}

                day28_event_cols = [
                    ("timezone", "TEXT DEFAULT 'Asia/Kolkata'"),
                    ("updated_at", "TEXT DEFAULT ''"),
                    ("event_status", "TEXT DEFAULT 'SCHEDULED'"),
                    ("reminder_state", "TEXT DEFAULT 'PENDING'"),
                    ("start_utc", "INTEGER DEFAULT 0"),
                    ("end_utc", "INTEGER DEFAULT 0"),
                    ("timezone_id", "TEXT DEFAULT 'Asia/Kolkata'"),
                    ("version", "INTEGER DEFAULT 1"),
                    ("source", "TEXT DEFAULT 'voice'"),
                    ("operation_id", "TEXT DEFAULT ''"),
                ]

                for col_name, col_def in day28_event_cols:
                    if col_name not in existing_cols:
                        conn.execute(f"ALTER TABLE events ADD COLUMN {col_name} {col_def};")
                        logger.info("Migrated 'events' table: added column '%s'", col_name)

                # 3. Create Day 28 event_reminders table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS event_reminders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id INTEGER NOT NULL,
                        event_version INTEGER NOT NULL DEFAULT 1,
                        reminder_type TEXT NOT NULL,
                        offset_seconds INTEGER NOT NULL,
                        due_at_utc INTEGER NOT NULL,
                        status TEXT NOT NULL DEFAULT 'PENDING',
                        attempt_count INTEGER DEFAULT 0,
                        claimed_at_utc INTEGER DEFAULT NULL,
                        delivered_at_utc INTEGER DEFAULT NULL,
                        last_error_code TEXT DEFAULT NULL,
                        created_at_utc INTEGER NOT NULL,
                        FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
                        UNIQUE(event_id, event_version, reminder_type)
                    );
                """)

                # 4. Indices for fast conflict checking & reminder due querying
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_start_utc ON events(start_utc);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_end_utc ON events(end_utc);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON events(event_status);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_reminders_due ON event_reminders(due_at_utc, status);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_reminders_event ON event_reminders(event_id, status);")

                # 5. Backfill start_utc and end_utc for legacy events where start_utc == 0
                _backfill_legacy_utc_timestamps(conn)

                # 6. Update schema version
                set_schema_version(conn, SCHEMA_VERSION)

            logger.info("Calendar database Day 28 initialization complete (version=%d)", SCHEMA_VERSION)
        finally:
            conn.close()


def _backfill_legacy_utc_timestamps(conn: sqlite3.Connection) -> None:
    """Calculate and populate start_utc and end_utc for legacy rows."""
    from .calendar_timezone_engine import parse_datetime_iso

    rows = conn.execute("SELECT id, start_iso, end_iso, timezone FROM events WHERE start_utc = 0 OR start_utc IS NULL;").fetchall()
    for row in rows:
        eid = row["id"]
        tz_name = row["timezone"] or "Asia/Kolkata"
        try:
            _, start_ms, _ = parse_datetime_iso(row["start_iso"], tz_name)
            _, end_ms, _ = parse_datetime_iso(row["end_iso"], tz_name)
            conn.execute(
                "UPDATE events SET start_utc = ?, end_utc = ?, timezone_id = ? WHERE id = ?;",
                (start_ms, end_ms, tz_name, eid)
            )
        except Exception as e:
            logger.debug("Skipping UTC backfill for event %d: %s", eid, e)


@contextmanager
def atomic_calendar_transaction(db_path: str | Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager acquiring a BEGIN IMMEDIATE write lock to ensure race-free
    conflict checking and event insertion.
    """
    conn = get_db_connection(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE;")
        yield conn
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error("Calendar transaction rolled back due to error: %s", exc)
        raise exc
    finally:
        conn.close()


def verify_calendar_database_health(db_path: str | Path | None = None) -> dict[str, Any]:
    """Perform health and integrity audit of calendar storage."""
    is_ok, msg = check_database_integrity(db_path)
    conn = get_db_connection(db_path)
    try:
        v = get_schema_version(conn)
        evt_count = conn.execute("SELECT COUNT(*) FROM events;").fetchone()[0]
        rem_count = conn.execute("SELECT COUNT(*) FROM event_reminders;").fetchone()[0]
        pending_rem = conn.execute("SELECT COUNT(*) FROM event_reminders WHERE status = 'PENDING';").fetchone()[0]
        return {
            "healthy": is_ok,
            "integrity_status": msg,
            "schema_version": v,
            "events_count": evt_count,
            "reminders_count": rem_count,
            "pending_reminders_count": pending_rem,
        }
    finally:
        conn.close()
