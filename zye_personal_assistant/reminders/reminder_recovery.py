"""
Restart Recovery & Stale Reminder Reconciliation Engine (Day 28).
Reconciles pending reminders, reclaims orphaned claims, and suppresses expired past alerts.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Union

from .reminder_repository import reclaim_stale_claims
from ..calendar.calendar_database import get_db_connection

logger = logging.getLogger("zye.personal_assistant.reminders.recovery")


def reconcile_reminders_on_startup(
    conn: Union[sqlite3.Connection, str, Path, None] = None,
    current_utc_ms: int | None = None,
) -> Dict[str, Any]:
    """
    Execute startup reconciliation:
      1. Reclaim stale CLAIMED reminders (abandoned during sudden crash/exit).
      2. Suppress pending reminders whose events have already started or concluded.
      3. Return audit summary.
    """
    close_after = False
    if conn is None or isinstance(conn, (str, Path)):
        active_conn = get_db_connection(conn)
        close_after = True
    else:
        active_conn = conn

    try:
        now_ms = current_utc_ms or int(time.time() * 1000)

        # 1. Reclaim stale claims (> 120s old)
        reclaimed_count = reclaim_stale_claims(active_conn, now_ms, stale_threshold_seconds=120)

        # 2. Suppress pending reminders for meetings that already started
        cursor = active_conn.execute(
            """
            UPDATE event_reminders
            SET status = 'SUPPRESSED', last_error_code = 'EXPIRED_ON_RESTART'
            WHERE status = 'PENDING'
              AND due_at_utc < ?
              AND event_id IN (
                  SELECT id FROM events WHERE start_utc <= ?
              );
            """,
            (now_ms, now_ms),
        )
        suppressed_count = cursor.rowcount
        if close_after:
            active_conn.commit()

        # 3. Count remaining active reminders
        pending_count = active_conn.execute(
            "SELECT COUNT(*) FROM event_reminders WHERE status = 'PENDING';"
        ).fetchone()[0]

        logger.info(
            "Startup reminder reconciliation: reclaimed=%d, expired_suppressed=%d, active_pending=%d",
            reclaimed_count,
            suppressed_count,
            pending_count,
        )

        return {
            "status": "RECONCILED",
            "reclaimed_claims_count": reclaimed_count,
            "expired_suppressed_count": suppressed_count,
            "active_pending_count": pending_count,
            "reclaimed_stale_claims": reclaimed_count,
            "suppressed_expired_reminders": suppressed_count,
            "timestamp_utc_ms": now_ms,
        }
    finally:
        if close_after:
            active_conn.close()
