"""
Persistent Reminder Storage & State Machine Repository (Day 28).
Manages multi-state transitions: PENDING -> CLAIMED -> DELIVERED / FAILED / SUPPRESSED / CANCELLED.
Guarantees duplicate prevention with unique constraint on (event_id, event_version, reminder_type).
"""

from __future__ import annotations

import logging
import sqlite3
import time
from typing import Any, Dict, List, Optional

from .reminder_models import ReminderStatus, ReminderType

logger = logging.getLogger("zye.personal_assistant.reminders.repository")


def create_reminders_for_event(
    conn: sqlite3.Connection,
    event_id: int,
    event_version: int,
    start_utc_ms: int,
    created_at_utc_ms: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Generate 15-minute and 2-minute persistent reminders for an event.
    Applies late-creation policy:
      - If created with <= 15m remaining, 15m reminder is marked SUPPRESSED.
      - If created with <= 2m remaining, 2m reminder is marked SUPPRESSED.
    """
    now_ms = created_at_utc_ms or int(time.time() * 1000)
    created_records: List[Dict[str, Any]] = []

    specs = [
        (ReminderType.FIFTEEN_MIN.value, 15 * 60, 15 * 60 * 1000),
        (ReminderType.TWO_MIN.value, 2 * 60, 2 * 60 * 1000),
    ]

    for r_type, offset_sec, offset_ms in specs:
        due_ms = start_utc_ms - offset_ms
        time_until_event_sec = (start_utc_ms - now_ms) / 1000.0

        # Late creation suppression policy
        if r_type == ReminderType.FIFTEEN_MIN.value and time_until_event_sec < (14.5 * 60):
            initial_status = ReminderStatus.SUPPRESSED.value
        elif r_type == ReminderType.TWO_MIN.value and time_until_event_sec < (1.5 * 60):
            initial_status = ReminderStatus.SUPPRESSED.value
        else:
            initial_status = ReminderStatus.PENDING.value

        try:
            cursor = conn.execute(
                """
                INSERT INTO event_reminders
                (event_id, event_version, reminder_type, offset_seconds, due_at_utc, status, attempt_count, created_at_utc)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?)
                ON CONFLICT(event_id, event_version, reminder_type) DO UPDATE SET
                    due_at_utc = excluded.due_at_utc,
                    status = excluded.status;
                """,
                (event_id, event_version, r_type, offset_sec, due_ms, initial_status, now_ms),
            )
            created_records.append({
                "reminder_type": r_type,
                "due_at_utc": due_ms,
                "status": initial_status,
                "offset_seconds": offset_sec,
            })
        except Exception as exc:
            logger.error("Failed to insert reminder %s for event %d: %s", r_type, event_id, exc)

    return created_records


def cancel_reminders_for_event(conn: sqlite3.Connection, event_id: int) -> int:
    """Mark all pending or claimed reminders for this event as CANCELLED."""
    cursor = conn.execute(
        """
        UPDATE event_reminders
        SET status = 'CANCELLED'
        WHERE event_id = ? AND status IN ('PENDING', 'CLAIMED');
        """,
        (event_id,),
    )
    return cursor.rowcount


def get_due_reminders(
    conn: sqlite3.Connection,
    current_utc_ms: Optional[int] = None,
    lookback_ms: int = 180000,  # 3-minute grace window
    as_of_utc_ms: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Find reminders that are due for delivery:
      - status == 'PENDING'
      - due_at_utc <= eff_utc_ms
      - due_at_utc >= (eff_utc_ms - lookback_ms)
      - event is not cancelled or deleted
    """
    eff_utc_ms = as_of_utc_ms or current_utc_ms or int(time.time() * 1000)
    min_due = eff_utc_ms - lookback_ms
    query = """
        SELECT r.id, r.event_id, r.event_version, r.reminder_type, r.offset_seconds, r.due_at_utc,
               e.title, e.start_iso, e.end_iso, e.location, e.timezone_id
        FROM event_reminders r
        JOIN events e ON r.event_id = e.id
        WHERE r.status = 'PENDING'
          AND r.due_at_utc <= ?
          AND r.due_at_utc >= ?
          AND e.event_status NOT IN ('CANCELLED', 'DELETED')
          AND r.event_version = e.version
        ORDER BY r.due_at_utc ASC;
    """
    rows = conn.execute(query, (eff_utc_ms, min_due)).fetchall()
    return [dict(r) for r in rows]


def claim_reminder(
    conn: sqlite3.Connection,
    reminder_id: int,
    current_utc_ms: Optional[int] = None,
    claimed_at_utc_ms: Optional[int] = None,
) -> bool:
    """Atomically claim a reminder for immediate delivery."""
    eff_ms = claimed_at_utc_ms or current_utc_ms or int(time.time() * 1000)
    cursor = conn.execute(
        """
        UPDATE event_reminders
        SET status = 'CLAIMED', claimed_at_utc = ?, attempt_count = attempt_count + 1
        WHERE id = ? AND status = 'PENDING';
        """,
        (eff_ms, reminder_id),
    )
    return cursor.rowcount > 0


def mark_reminder_delivered(
    conn: sqlite3.Connection,
    reminder_id: int,
    current_utc_ms: Optional[int] = None,
    delivered_at_utc_ms: Optional[int] = None,
) -> bool:
    """Mark reminder as successfully delivered."""
    eff_ms = delivered_at_utc_ms or current_utc_ms or int(time.time() * 1000)
    cursor = conn.execute(
        """
        UPDATE event_reminders
        SET status = 'DELIVERED', delivered_at_utc = ?
        WHERE id = ?;
        """,
        (eff_ms, reminder_id),
    )
    return cursor.rowcount > 0


def mark_reminder_failed(
    conn: sqlite3.Connection,
    reminder_id: int,
    error_code: str = "DELIVERY_FAILED",
    current_utc_ms: Optional[int] = None,
) -> bool:
    """Record reminder delivery failure."""
    cursor = conn.execute(
        """
        UPDATE event_reminders
        SET status = 'FAILED', last_error_code = ?
        WHERE id = ?;
        """,
        (error_code, reminder_id),
    )
    return cursor.rowcount > 0


def reclaim_stale_claims(conn: sqlite3.Connection, current_utc_ms: int, stale_threshold_seconds: int = 120) -> int:
    """Reclaim reminders stuck in CLAIMED state due to unhandled crash or audio failure."""
    cutoff = current_utc_ms - (stale_threshold_seconds * 1000)
    cursor = conn.execute(
        """
        UPDATE event_reminders
        SET status = 'PENDING', claimed_at_utc = NULL
        WHERE status = 'CLAIMED' AND claimed_at_utc < ?;
        """,
        (cutoff,),
    )
    return cursor.rowcount


def get_reminders_for_event(conn: sqlite3.Connection, event_id: int) -> List[Dict[str, Any]]:
    """Get all persistent reminders associated with an event."""
    rows = conn.execute(
        """
        SELECT id, event_id, event_version, reminder_type, offset_seconds, due_at_utc, status,
               attempt_count, claimed_at_utc, delivered_at_utc, last_error_code, created_at_utc
        FROM event_reminders
        WHERE event_id = ?
        ORDER BY due_at_utc ASC;
        """,
        (event_id,),
    ).fetchall()
    return [dict(r) for r in rows]
