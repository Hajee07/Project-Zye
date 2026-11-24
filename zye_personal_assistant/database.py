"""
Unified SQLite Database Engine for Zye Personal Assistant (Day 14).
Provides atomic schema initialization, migrations, connection management,
thread-safety, and database backup / recovery.
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("zye.personal_assistant.database")

_DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DB_PATH = _DEFAULT_DB_DIR / "zye_assistant_db.sqlite"

_DB_LOCK = threading.RLock()
_TEMP_TEST_DB_PATH: Path | None = None


def get_default_db_path() -> Path:
    _DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_DB_PATH


def get_db_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """
    Open a connection to the SQLite database with row factory, busy timeout,
    and foreign key enforcement enabled.
    When db_path == ':memory:', uses a persistent test temp file so connections share state.
    """
    global _TEMP_TEST_DB_PATH

    if str(db_path) == ":memory:":
        with _DB_LOCK:
            if _TEMP_TEST_DB_PATH is None or not _TEMP_TEST_DB_PATH.exists():
                import tempfile
                tf = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
                tf.close()
                _TEMP_TEST_DB_PATH = Path(tf.name)
            target = _TEMP_TEST_DB_PATH
    else:
        target = Path(db_path) if db_path is not None else get_default_db_path()
        target.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(target), timeout=15.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
    except sqlite3.OperationalError:
        pass
    return conn



def init_assistant_database(db_path: str | Path | None = None) -> None:
    """
    Initialize all Personal Assistant tables and indexes.
    Preserves any existing tables and applies backward-compatible column migrations.
    """
    with _DB_LOCK:
        conn = get_db_connection(db_path)
        try:
            with conn:
                # 1. EVENTS TABLE (Section 6.1)
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
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_start ON events(start_iso);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON events(event_status);")

                # 2. TASKS TABLE (Section 6.2)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        priority TEXT DEFAULT 'MEDIUM',
                        due_iso TEXT DEFAULT '',
                        est_minutes INTEGER DEFAULT 30,
                        project_name TEXT DEFAULT 'General',
                        status TEXT DEFAULT 'PENDING',
                        created_at TEXT DEFAULT (datetime('now')),
                        updated_at TEXT DEFAULT (datetime('now')),
                        scheduled_start_iso TEXT DEFAULT '',
                        scheduled_end_iso TEXT DEFAULT '',
                        linked_event_id INTEGER DEFAULT NULL,
                        FOREIGN KEY (linked_event_id) REFERENCES events(id) ON DELETE SET NULL
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_iso);")

                # 3. PROJECTS TABLE (Section 6.3)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS projects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        objective TEXT DEFAULT '',
                        deadline_iso TEXT DEFAULT '',
                        status TEXT DEFAULT 'ACTIVE',
                        blockers TEXT DEFAULT '',
                        created_at TEXT DEFAULT (datetime('now')),
                        updated_at TEXT DEFAULT (datetime('now')),
                        completion_percent REAL DEFAULT 0.0,
                        risk_level TEXT DEFAULT 'LOW',
                        owner TEXT DEFAULT 'User'
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);")

                # 4. DOCUMENT INDEX TABLE (Section 6.4)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS doc_index (
                        path TEXT PRIMARY KEY,
                        filename TEXT,
                        category TEXT,
                        modified_at TEXT,
                        snippet TEXT,
                        file_size INTEGER DEFAULT 0,
                        content_hash TEXT DEFAULT '',
                        indexed_at TEXT DEFAULT (datetime('now')),
                        processing_status TEXT DEFAULT 'INDEXED'
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_category ON doc_index(category);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_filename ON doc_index(filename);")

                # 5. EMAIL DRAFTS TABLE (Section 6.5)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS email_drafts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        to_addr TEXT NOT NULL,
                        subject TEXT NOT NULL,
                        body TEXT NOT NULL,
                        attachments TEXT DEFAULT '[]',
                        tone TEXT DEFAULT 'Professional',
                        priority TEXT DEFAULT 'MEDIUM',
                        created_at TEXT DEFAULT (datetime('now')),
                        status TEXT DEFAULT 'DRAFT'
                    );
                """)

                # 6. EMAIL ACTION HISTORY TABLE (Section 6.5)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS email_action_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action_type TEXT NOT NULL,
                        to_addr TEXT NOT NULL,
                        subject TEXT NOT NULL,
                        status TEXT NOT NULL,
                        details TEXT DEFAULT '',
                        timestamp TEXT DEFAULT (datetime('now'))
                    );
                """)

                # 7. TASK TIMEBLOCKS TABLE (Section 6.5)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS task_timeblocks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id INTEGER NOT NULL,
                        event_id INTEGER,
                        block_start TEXT NOT NULL,
                        block_end TEXT NOT NULL,
                        created_at TEXT DEFAULT (datetime('now')),
                        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                        FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE SET NULL
                    );
                """)

                # 8. PROJECT MILESTONES TABLE (Section 6.5)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS project_milestones (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id INTEGER NOT NULL,
                        title TEXT NOT NULL,
                        target_date TEXT DEFAULT '',
                        completed INTEGER DEFAULT 0,
                        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                    );
                """)

                # 9. RESEARCH HISTORY TABLE (Section 6.5)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS research_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        topic TEXT NOT NULL,
                        depth TEXT DEFAULT 'EXECUTIVE_BRIEF',
                        summary TEXT NOT NULL,
                        sources TEXT DEFAULT '[]',
                        uncertainties TEXT DEFAULT '[]',
                        created_at TEXT DEFAULT (datetime('now'))
                    );
                """)

                # 10. TRAVEL PLANS TABLE (Section 6.5)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS travel_plans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        destination TEXT NOT NULL,
                        days INTEGER NOT NULL,
                        purpose TEXT DEFAULT 'Business & Exploration',
                        budget_tier TEXT DEFAULT 'Moderate',
                        itinerary_json TEXT NOT NULL,
                        created_at TEXT DEFAULT (datetime('now'))
                    );
                """)

                # 11. AUDIT HISTORY TABLE (Section 6.5)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action_type TEXT NOT NULL,
                        target_resources TEXT DEFAULT '',
                        premortem_risk TEXT DEFAULT 'LOW',
                        authorized INTEGER DEFAULT 1,
                        result_status TEXT DEFAULT 'SUCCESS',
                        details TEXT DEFAULT '',
                        timestamp TEXT DEFAULT (datetime('now'))
                    );
                """)

                # 12. RUN BACKWARD-COMPATIBLE COLUMN MIGRATIONS
                _run_migrations(conn)

        finally:
            conn.close()


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Add any missing columns to existing tables without data loss."""
    migrations = {
        "events": [
            ("timezone", "TEXT DEFAULT 'Asia/Kolkata'"),
            ("created_at", "TEXT DEFAULT (datetime('now'))"),
            ("updated_at", "TEXT DEFAULT (datetime('now'))"),
            ("event_status", "TEXT DEFAULT 'SCHEDULED'"),
            ("reminder_state", "TEXT DEFAULT 'PENDING'"),
        ],
        "tasks": [
            ("created_at", "TEXT DEFAULT (datetime('now'))"),
            ("updated_at", "TEXT DEFAULT (datetime('now'))"),
            ("scheduled_start_iso", "TEXT DEFAULT ''"),
            ("scheduled_end_iso", "TEXT DEFAULT ''"),
            ("linked_event_id", "INTEGER DEFAULT NULL"),
        ],
        "projects": [
            ("created_at", "TEXT DEFAULT (datetime('now'))"),
            ("updated_at", "TEXT DEFAULT (datetime('now'))"),
            ("completion_percent", "REAL DEFAULT 0.0"),
            ("risk_level", "TEXT DEFAULT 'LOW'"),
            ("owner", "TEXT DEFAULT 'User'"),
        ],
        "doc_index": [
            ("file_size", "INTEGER DEFAULT 0"),
            ("content_hash", "TEXT DEFAULT ''"),
            ("indexed_at", "TEXT DEFAULT (datetime('now'))"),
            ("processing_status", "TEXT DEFAULT 'INDEXED'"),
        ],
        "email_drafts": [
            ("priority", "TEXT DEFAULT 'MEDIUM'"),
        ],
    }

    for table, columns in migrations.items():
        cursor = conn.execute(f"PRAGMA table_info({table});")
        existing_cols = {row["name"] for row in cursor.fetchall()}
        for col_name, col_def in columns:
            if col_name not in existing_cols:
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def};")
                    logger.info("Migrated table '%s': added column '%s'", table, col_name)
                except sqlite3.OperationalError as e:
                    logger.debug("Migration note for %s.%s: %s", table, col_name, e)


def backup_database(db_path: str | Path | None = None, backup_dir: str | Path | None = None) -> Optional[Path]:
    """Create a point-in-time SQLite backup using sqlite3.Connection.backup()."""
    source_path = Path(db_path) if db_path else get_default_db_path()
    if not source_path.exists() or str(source_path) == ":memory:":
        return None

    dest_dir = Path(backup_dir) if backup_dir else source_path.parent.parent / "backups"
    dest_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = dest_dir / f"zye_assistant_backup_{timestamp}.sqlite"

    with _DB_LOCK:
        src_conn = sqlite3.connect(str(source_path))
        dest_conn = sqlite3.connect(str(backup_file))
        try:
            with dest_conn:
                src_conn.backup(dest_conn)
            logger.info("Database backup created successfully: %s", backup_file)
            return backup_file
        finally:
            src_conn.close()
            dest_conn.close()


def check_database_integrity(db_path: str | Path | None = None) -> tuple[bool, str]:
    """Execute PRAGMA integrity_check and return (is_healthy, status_message)."""
    conn = get_db_connection(db_path)
    try:
        row = conn.execute("PRAGMA integrity_check;").fetchone()
        status = row[0] if row else "unknown"
        return (status == "ok", status)
    except Exception as e:
        return (False, str(e))
    finally:
        conn.close()
