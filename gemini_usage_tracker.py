"""
Gemini Usage Tracker & Budget Controller — Zye Multi-Project Gemini Intelligence Infrastructure v2.0 (Section 11).
Tracks per-request token telemetry, separates input/output/thinking/cached tokens, enforces daily/monthly
project and global budgets, and persists all usage events to SQLite.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from gemini_db import get_db_connection, init_gemini_database

logger = logging.getLogger("zye.gemini.usage_tracker")


@dataclass
class UsageRecord:
    request_id: str
    workload_id: str
    module_name: str
    project_id: str
    key_alias: str
    model_id: str
    thinking_level: str
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    duration_seconds: float = 0.0
    status: str = "SUCCESS"  # SUCCESS, FAILED, CACHED
    error_category: str | None = None
    prompt_hash: str | None = None


class GeminiUsageTracker:
    """
    Tracks and persists token consumption, monitors budgets, and raises warnings.
    """

    def __init__(self, db_path: str | None = None, auto_init: bool = True) -> None:
        self._db_path = db_path
        self._lock = threading.RLock()

        if auto_init:
            init_gemini_database(self._db_path)
            self._ensure_default_budgets()

    def record_event(self, record: UsageRecord) -> None:
        """Persist a single usage event to gemini_usage_events and gemini_request_history."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = get_db_connection(self._db_path)
            try:
                with conn:
                    # Insert usage event
                    conn.execute("""
                        INSERT INTO gemini_usage_events
                        (request_id, workload_id, module_name, project_id, key_alias, model_id, thinking_level,
                         input_tokens, output_tokens, thinking_tokens, total_tokens, cached_tokens,
                         request_duration, status, error_category, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, (
                        record.request_id,
                        record.workload_id,
                        record.module_name,
                        record.project_id,
                        record.key_alias,
                        record.model_id,
                        record.thinking_level,
                        record.input_tokens,
                        record.output_tokens,
                        record.thinking_tokens,
                        record.total_tokens,
                        record.cached_tokens,
                        record.duration_seconds,
                        record.status,
                        record.error_category,
                        now,
                    ))

                    # Insert request history
                    slot_id = 1
                    if "PROJECT_" in record.key_alias:
                        try:
                            slot_id = int(record.key_alias.replace("PROJECT_", ""))
                        except ValueError:
                            pass

                    conn.execute("""
                        INSERT OR REPLACE INTO gemini_request_history
                        (request_id, workload_id, module_name, slot_id, model_id, thinking_level,
                         prompt_hash, cached, tokens_used, duration_seconds, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, (
                        record.request_id,
                        record.workload_id,
                        record.module_name,
                        slot_id,
                        record.model_id,
                        record.thinking_level,
                        record.prompt_hash,
                        1 if record.status == "CACHED" else 0,
                        record.total_tokens,
                        record.duration_seconds,
                        record.status,
                        now,
                    ))

                    # Update budget accumulators
                    if record.total_tokens > 0:
                        self._increment_budget_counters(conn, record.project_id, record.total_tokens)

            except Exception as exc:
                logger.warning("Failed to record usage event: %s", exc)
            finally:
                conn.close()

    def _increment_budget_counters(self, conn: Any, project_id: str, tokens: int) -> None:
        """Increment daily and monthly tokens for GLOBAL and PROJECT scopes."""
        now = datetime.now(timezone.utc).isoformat()
        # Update GLOBAL
        conn.execute("""
            UPDATE gemini_budget_settings
            SET current_daily_tokens = current_daily_tokens + ?,
                current_monthly_tokens = current_monthly_tokens + ?,
                updated_at = ?
            WHERE scope_type = 'GLOBAL';
        """, (tokens, tokens, now))

        # Update Project-specific if exists
        conn.execute("""
            UPDATE gemini_budget_settings
            SET current_daily_tokens = current_daily_tokens + ?,
                current_monthly_tokens = current_monthly_tokens + ?,
                updated_at = ?
            WHERE scope_type = 'PROJECT' AND scope_id = ?;
        """, (tokens, tokens, now, project_id))

    def check_budget(self, project_id: str | None = None) -> tuple[bool, str]:
        """
        Check if daily or monthly budget has been exceeded.
        Returns (is_allowed, reason).
        """
        with self._lock:
            conn = get_db_connection(self._db_path)
            try:
                # Check GLOBAL first
                row = conn.execute("""
                    SELECT daily_token_budget, monthly_token_budget, current_daily_tokens, current_monthly_tokens, warning_threshold_pct
                    FROM gemini_budget_settings WHERE scope_type = 'GLOBAL';
                """).fetchone()

                if row:
                    daily_limit = row["daily_token_budget"]
                    monthly_limit = row["monthly_token_budget"]
                    daily_cur = row["current_daily_tokens"]
                    monthly_cur = row["current_monthly_tokens"]

                    if daily_cur >= daily_limit:
                        return False, f"Global daily token budget exceeded ({daily_cur}/{daily_limit})"
                    if monthly_cur >= monthly_limit:
                        return False, f"Global monthly token budget exceeded ({monthly_cur}/{monthly_limit})"

                # Check Project if given
                if project_id:
                    prow = conn.execute("""
                        SELECT daily_token_budget, monthly_token_budget, current_daily_tokens, current_monthly_tokens
                        FROM gemini_budget_settings WHERE scope_type = 'PROJECT' AND scope_id = ?;
                    """, (project_id,)).fetchone()

                    if prow:
                        p_daily_limit = prow["daily_token_budget"]
                        p_monthly_limit = prow["monthly_token_budget"]
                        p_daily_cur = prow["current_daily_tokens"]
                        p_monthly_cur = prow["current_monthly_tokens"]

                        if p_daily_cur >= p_daily_limit:
                            return False, f"Project {project_id} daily token budget exceeded ({p_daily_cur}/{p_daily_limit})"
                        if p_monthly_cur >= p_monthly_limit:
                            return False, f"Project {project_id} monthly token budget exceeded ({p_monthly_cur}/{p_monthly_limit})"

                return True, "OK"
            except Exception as exc:
                logger.warning("Error checking budget: %s", exc)
                return True, "OK"
            finally:
                conn.close()

    def get_token_statistics(self) -> dict[str, Any]:
        """Return aggregated token metrics across all projects."""
        with self._lock:
            conn = get_db_connection(self._db_path)
            try:
                stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total_requests,
                        COALESCE(SUM(input_tokens), 0) as total_input,
                        COALESCE(SUM(output_tokens), 0) as total_output,
                        COALESCE(SUM(thinking_tokens), 0) as total_thinking,
                        COALESCE(SUM(cached_tokens), 0) as total_cached,
                        COALESCE(SUM(total_tokens), 0) as grand_total,
                        COALESCE(AVG(request_duration), 0.0) as avg_duration
                    FROM gemini_usage_events;
                """).fetchone()

                return {
                    "total_requests": stats["total_requests"] if stats else 0,
                    "total_input_tokens": stats["total_input"] if stats else 0,
                    "total_output_tokens": stats["total_output"] if stats else 0,
                    "total_thinking_tokens": stats["total_thinking"] if stats else 0,
                    "total_cached_tokens": stats["total_cached"] if stats else 0,
                    "grand_total_tokens": stats["grand_total"] if stats else 0,
                    "average_duration_seconds": round(stats["avg_duration"], 3) if stats else 0.0,
                }
            finally:
                conn.close()

    def _ensure_default_budgets(self) -> None:
        """Initialize global budget rows if not present."""
        now = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection(self._db_path)
        try:
            with conn:
                conn.execute("""
                    INSERT OR IGNORE INTO gemini_budget_settings
                    (scope_type, scope_id, daily_token_budget, monthly_token_budget, warning_threshold_pct, current_daily_tokens, current_monthly_tokens, updated_at)
                    VALUES ('GLOBAL', 'ALL', 5000000, 100000000, 80.0, 0, 0, ?);
                """, (now,))
        finally:
            conn.close()
