"""
Persistent Meeting Reminder Scheduler & Dispatch Engine (Day 28).
Inspects SQLite event_reminders, atomically claims due alerts, generates multi-lingual
messages, updates delivery states, and synchronizes legacy events table flags.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from zye_personal_assistant.database import _DB_LOCK, get_db_connection
from zye_personal_assistant.calendar.calendar_database import (
    atomic_calendar_transaction,
    initialize_calendar_database,
)
from zye_personal_assistant.calendar.calendar_timezone_engine import (
    convert_local_to_utc,
    convert_utc_to_local,
    get_zone_info,
    parse_datetime_iso,
)

from .reminder_models import ReminderStatus, ReminderType
from .reminder_recovery import reconcile_reminders_on_startup
from .reminder_repository import (
    cancel_reminders_for_event,
    claim_reminder,
    create_reminders_for_event,
    get_due_reminders,
    mark_reminder_delivered,
    mark_reminder_failed,
)
from .reminder_voice_bridge import build_calendar_reminder_message

logger = logging.getLogger("zye.personal_assistant.reminders.scheduler")


class PersistentReminderScheduler:
    """
    Evaluator for scheduled meeting reminders.
    Integrates directly with the 45-second daemon in main.py.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        default_timezone: str = "Asia/Kolkata",
    ) -> None:
        self._db_path = db_path
        self._default_tz = default_timezone
        initialize_calendar_database(self._db_path)
        self._reconciled = False

    def ensure_startup_reconciliation(self) -> None:
        """Run startup reconciliation once."""
        if not self._reconciled:
            with _DB_LOCK:
                conn = get_db_connection(self._db_path)
                try:
                    reconcile_reminders_on_startup(conn)
                    self._reconciled = True
                finally:
                    conn.close()

    def check_due_reminders(self, reference_time_iso: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Check and claim due reminders for immediate voice dispatch.
        Returns active alerts with voice messages in English, Tanglish, and Tamil.
        """
        self.ensure_startup_reconciliation()

        if reference_time_iso:
            try:
                _, now_ms, _ = parse_datetime_iso(reference_time_iso, self._default_tz)
            except Exception:
                now_ms = int(time.time() * 1000)
        else:
            now_ms = int(time.time() * 1000)

        alerts: List[Dict[str, Any]] = []

        with _DB_LOCK:
            with atomic_calendar_transaction(self._db_path) as conn:
                due_records = get_due_reminders(conn, current_utc_ms=now_ms)

                for r in due_records:
                    rem_id = r["id"]
                    event_id = r["event_id"]
                    r_type = r["reminder_type"]
                    title = r["title"]
                    location = r.get("location") or "online"
                    event_start_iso = r["start_iso"]

                    # Atomically claim
                    claimed = claim_reminder(conn, rem_id, now_ms)
                    if not claimed:
                        continue  # Another worker or transaction claimed it

                    # Calculate minutes left
                    try:
                        _, start_ms, _ = parse_datetime_iso(event_start_iso, self._default_tz)
                        diff_sec = (start_ms - now_ms) / 1000.0
                        minutes_left = max(0, round(diff_sec / 60.0))
                    except Exception:
                        minutes_left = 15 if r_type == ReminderType.FIFTEEN_MIN.value else 2

                    # Build multi-lingual messages
                    msgs = build_calendar_reminder_message(
                        title=title,
                        reminder_type=r_type,
                        minutes_left=minutes_left,
                        location=location,
                    )

                    alert_payload = {
                        "reminder_id": rem_id,
                        "event_id": event_id,
                        "title": title,
                        "reminder_type": r_type,
                        "minutes_left": minutes_left,
                        "location": location,
                        "message_en": msgs["message_en"],
                        "message_tanglish": msgs["message_tanglish"],
                        "message_tamil": msgs["message_tamil"],
                    }

                    # Mark DELIVERED in database
                    mark_reminder_delivered(conn, rem_id, now_ms)

                    # Synchronize legacy columns on events table for backward compatibility
                    if r_type == ReminderType.FIFTEEN_MIN.value:
                        conn.execute("UPDATE events SET reminded_15m = 1 WHERE id = ?;", (event_id,))
                    elif r_type == ReminderType.TWO_MIN.value:
                        conn.execute("UPDATE events SET reminded_2m = 1 WHERE id = ?;", (event_id,))

                    alerts.append(alert_payload)
                    logger.info("Dispatched reminder [%s] for event '%s' (id=%d)", r_type, title, event_id)

        return alerts

    def get_scheduler_status(self) -> Dict[str, Any]:
        """Return diagnostic metrics of reminder scheduler."""
        with _DB_LOCK:
            conn = get_db_connection(self._db_path)
            try:
                counts = {}
                for st in ("PENDING", "CLAIMED", "DELIVERED", "SUPPRESSED", "CANCELLED", "FAILED"):
                    c = conn.execute("SELECT COUNT(*) FROM event_reminders WHERE status = ?;", (st,)).fetchone()[0]
                    counts[st.lower()] = c
                return {
                    "scheduler_active": True,
                    "default_timezone": self._default_tz,
                    "reminder_counts": counts,
                }
            finally:
                conn.close()
