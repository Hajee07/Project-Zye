"""
Gemini Intelligence Infrastructure — Database Subsystem (Section 18).
Manages SQLite schemas, migrations, telemetry persistence, and audit records
in data/zye_assistant_db.sqlite.
"""

from __future__ import annotations

import logging
import os
import pathlib
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("zye.gemini.db")

DEFAULT_DB_PATH = pathlib.Path.cwd() / "data" / "zye_assistant_db.sqlite"
_DB_LOCK = threading.RLock()
_TEMP_TEST_DB_PATH: pathlib.Path | None = None


def get_db_connection(db_path: pathlib.Path | str | None = None) -> sqlite3.Connection:
    """Return configured SQLite connection with row_factory and WAL mode."""
    global _TEMP_TEST_DB_PATH

    if db_path == ":memory:":
        with _DB_LOCK:
            if _TEMP_TEST_DB_PATH is None or not _TEMP_TEST_DB_PATH.exists():
                import tempfile
                tf = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
                tf.close()
                _TEMP_TEST_DB_PATH = pathlib.Path(tf.name)
            target = _TEMP_TEST_DB_PATH
    else:
        target = pathlib.Path(db_path or DEFAULT_DB_PATH)

    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=20.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_gemini_database(db_path: pathlib.Path | str | None = None) -> None:
    """
    Initialize all 9 Section 18 tables with appropriate indexes and migrations.
    Never drops or mutates existing tables (e.g. repair_approvals).
    """
    with _DB_LOCK:
        conn = get_db_connection(db_path)
        try:
            with conn:
                # 1. Project Registry
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS gemini_project_registry (
                        slot_id INTEGER PRIMARY KEY,
                        project_alias TEXT UNIQUE NOT NULL,
                        project_id TEXT NOT NULL,
                        account_alias TEXT NOT NULL,
                        assigned_workloads TEXT DEFAULT '[]',
                        status TEXT DEFAULT 'CONFIGURED',
                        billing_status TEXT DEFAULT 'UNKNOWN',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                """)

                # 2. Key Metadata (Never stores raw secret keys)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS gemini_key_metadata (
                        slot_id INTEGER PRIMARY KEY,
                        account_alias TEXT NOT NULL,
                        project_alias TEXT NOT NULL,
                        masked_key TEXT NOT NULL,
                        env_key_var TEXT NOT NULL,
                        env_project_var TEXT NOT NULL,
                        auth_status TEXT DEFAULT 'UNCONFIGURED',
                        key_health TEXT DEFAULT 'UNKNOWN',
                        last_used_at TEXT,
                        total_requests INTEGER DEFAULT 0,
                        successful_requests INTEGER DEFAULT 0,
                        failed_requests INTEGER DEFAULT 0,
                        total_tokens INTEGER DEFAULT 0,
                        updated_at TEXT NOT NULL
                    );
                """)

                # 3. Model & Thinking Settings
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS gemini_model_settings (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        model_id TEXT NOT NULL DEFAULT 'gemini-3.5-flash-lite',
                        thinking_level TEXT NOT NULL DEFAULT 'LOW',
                        thinking_mode TEXT NOT NULL DEFAULT 'MANUAL',
                        system_instruction TEXT,
                        temperature REAL DEFAULT 0.5,
                        updated_at TEXT NOT NULL
                    );
                """)

                # 4. Usage Events (granular per-request telemetry)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS gemini_usage_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        request_id TEXT NOT NULL,
                        workload_id TEXT NOT NULL,
                        module_name TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        key_alias TEXT NOT NULL,
                        model_id TEXT NOT NULL,
                        thinking_level TEXT NOT NULL,
                        input_tokens INTEGER DEFAULT 0,
                        output_tokens INTEGER DEFAULT 0,
                        thinking_tokens INTEGER DEFAULT 0,
                        total_tokens INTEGER DEFAULT 0,
                        cached_tokens INTEGER DEFAULT 0,
                        request_duration REAL DEFAULT 0.0,
                        status TEXT NOT NULL,
                        error_category TEXT,
                        timestamp TEXT NOT NULL
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_project ON gemini_usage_events(project_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON gemini_usage_events(timestamp);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_workload ON gemini_usage_events(workload_id);")

                # 5. Request History
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS gemini_request_history (
                        request_id TEXT PRIMARY KEY,
                        workload_id TEXT NOT NULL,
                        module_name TEXT NOT NULL,
                        slot_id INTEGER NOT NULL,
                        model_id TEXT NOT NULL,
                        thinking_level TEXT NOT NULL,
                        prompt_hash TEXT,
                        cached INTEGER DEFAULT 0,
                        tokens_used INTEGER DEFAULT 0,
                        duration_seconds REAL DEFAULT 0.0,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                """)

                # 6. Task Decomposition History
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS gemini_task_history (
                        task_id TEXT PRIMARY KEY,
                        complexity TEXT NOT NULL,
                        subtasks_count INTEGER DEFAULT 0,
                        parallel_workers_count INTEGER DEFAULT 0,
                        status TEXT NOT NULL,
                        total_tokens INTEGER DEFAULT 0,
                        duration_seconds REAL DEFAULT 0.0,
                        created_at TEXT NOT NULL
                    );
                """)

                # 7. Parallel Jobs
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS gemini_parallel_jobs (
                        job_id TEXT PRIMARY KEY,
                        task_id TEXT NOT NULL,
                        worker_role TEXT NOT NULL,
                        slot_id INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        error TEXT,
                        tokens_used INTEGER DEFAULT 0,
                        created_at TEXT NOT NULL,
                        completed_at TEXT
                    );
                """)

                # 8. Budget Settings
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS gemini_budget_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        scope_type TEXT NOT NULL, -- 'GLOBAL' or 'PROJECT'
                        scope_id TEXT NOT NULL,   -- 'ALL' or 'PROJECT_01'
                        daily_token_budget INTEGER DEFAULT 1000000,
                        monthly_token_budget INTEGER DEFAULT 25000000,
                        warning_threshold_pct REAL DEFAULT 80.0,
                        current_daily_tokens INTEGER DEFAULT 0,
                        current_monthly_tokens INTEGER DEFAULT 0,
                        updated_at TEXT NOT NULL,
                        UNIQUE(scope_type, scope_id)
                    );
                """)

                # 9. Error History
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS gemini_error_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        request_id TEXT,
                        slot_id INTEGER,
                        project_id TEXT,
                        status_code INTEGER,
                        error_type TEXT NOT NULL,
                        sanitized_message TEXT NOT NULL,
                        retry_count INTEGER DEFAULT 0,
                        retry_after_seconds REAL DEFAULT 0.0,
                        timestamp TEXT NOT NULL
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_err_slot ON gemini_error_history(slot_id);")

                # Insert default model settings if not already present
                now = datetime.now(timezone.utc).isoformat()
                conn.execute("""
                    INSERT OR IGNORE INTO gemini_model_settings 
                    (id, model_id, thinking_level, thinking_mode, system_instruction, temperature, updated_at)
                    VALUES (1, 'gemini-3.5-flash-lite', 'LOW', 'MANUAL', 'You are Zye, an autonomous AI assistant.', 0.5, ?);
                """, (now,))

            logger.info("Gemini Intelligence database tables initialized successfully.")
        finally:
            conn.close()


def verify_gemini_database(db_path: pathlib.Path | str | None = None) -> dict[str, bool]:
    """Verify presence and integrity of all Gemini database tables."""
    with _DB_LOCK:
        conn = get_db_connection(db_path)
        try:
            expected_tables = [
                "gemini_project_registry",
                "gemini_key_metadata",
                "gemini_model_settings",
                "gemini_usage_events",
                "gemini_request_history",
                "gemini_task_history",
                "gemini_parallel_jobs",
                "gemini_budget_settings",
                "gemini_error_history",
            ]
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
            existing = {row["name"] for row in cursor.fetchall()}
            return {tbl: (tbl in existing) for tbl in expected_tables}
        finally:
            conn.close()
