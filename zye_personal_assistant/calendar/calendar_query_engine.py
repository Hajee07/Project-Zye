"""
Advanced Calendar Query & Schedule Summary Engine (Day 28).
Provides fast, indexed, timezone-aware schedule queries:
  - get_today_events, get_tomorrow_events, get_week_events
  - get_next_meeting, search_events, get_upcoming_events, calendar summaries.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from zye_personal_assistant.database import _DB_LOCK, get_db_connection

from .calendar_database import initialize_calendar_database
from .calendar_models import CalendarEventRead
from .calendar_timezone_engine import (
    convert_local_to_utc,
    convert_utc_to_local,
    get_configured_timezone,
    get_current_local_datetime,
    get_zone_info,
    parse_datetime_iso,
)

logger = logging.getLogger("zye.personal_assistant.calendar.query")


class CalendarQueryEngine:
    """Indexed calendar query engine delivering fast, timezone-aware schedule responses."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        default_timezone: str = "Asia/Kolkata",
    ) -> None:
        self._db_path = db_path
        self._default_tz = get_configured_timezone(default_timezone)
        initialize_calendar_database(self._db_path)

    def _row_to_event(self, row: sqlite3.Row) -> CalendarEventRead:
        return CalendarEventRead(
            id=row["id"],
            title=row["title"],
            start_iso=row["start_iso"],
            end_iso=row["end_iso"],
            start_utc_ms=row["start_utc"] or 0,
            end_utc_ms=row["end_utc"] or 0,
            timezone_id=row["timezone_id"] or row["timezone"] or self._default_tz,
            location=row["location"] or "",
            notes=row["notes"] or "",
            event_status=row["event_status"] or "SCHEDULED",
            version=row["version"] or 1,
            reminded_15m=row["reminded_15m"] or 0,
            reminded_2m=row["reminded_2m"] or 0,
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
        )

    def get_events_for_day(self, target_date: datetime, timezone_id: Optional[str] = None) -> List[CalendarEventRead]:
        """Fetch all non-cancelled events occurring on the target local day."""
        tz_name = get_configured_timezone(timezone_id or self._default_tz)
        tz = get_zone_info(tz_name)
        target_local = target_date.astimezone(tz) if target_date.tzinfo else target_date.replace(tzinfo=tz)

        day_start = target_local.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = target_local.replace(hour=23, minute=59, second=59, microsecond=999999)

        start_ms, _ = convert_local_to_utc(day_start, tz_name)
        end_ms, _ = convert_local_to_utc(day_end, tz_name)

        with _DB_LOCK:
            conn = get_db_connection(self._db_path)
            try:
                rows = conn.execute(
                    """
                    SELECT * FROM events
                    WHERE event_status NOT IN ('CANCELLED', 'DELETED')
                      AND start_utc < ? AND end_utc > ?
                    ORDER BY start_utc ASC;
                    """,
                    (end_ms, start_ms),
                ).fetchall()
                return [self._row_to_event(r) for r in rows]
            finally:
                conn.close()

    def get_today_events(self, timezone_id: Optional[str] = None) -> List[CalendarEventRead]:
        """Get today's schedule."""
        now_local = get_current_local_datetime(timezone_id or self._default_tz)
        return self.get_events_for_day(now_local, timezone_id)

    def get_tomorrow_events(self, timezone_id: Optional[str] = None) -> List[CalendarEventRead]:
        """Get tomorrow's schedule."""
        now_local = get_current_local_datetime(timezone_id or self._default_tz)
        tomorrow_local = now_local + timedelta(days=1)
        return self.get_events_for_day(tomorrow_local, timezone_id)

    def get_week_events(self, timezone_id: Optional[str] = None) -> List[CalendarEventRead]:
        """Get all scheduled events for the upcoming 7 days."""
        tz_name = get_configured_timezone(timezone_id or self._default_tz)
        now_local = get_current_local_datetime(tz_name)
        start_ms, _ = convert_local_to_utc(now_local.replace(hour=0, minute=0, second=0), tz_name)
        end_ms = start_ms + (7 * 24 * 60 * 60 * 1000)

        with _DB_LOCK:
            conn = get_db_connection(self._db_path)
            try:
                rows = conn.execute(
                    """
                    SELECT * FROM events
                    WHERE event_status NOT IN ('CANCELLED', 'DELETED')
                      AND start_utc >= ? AND start_utc <= ?
                    ORDER BY start_utc ASC;
                    """,
                    (start_ms, end_ms),
                ).fetchall()
                return [self._row_to_event(r) for r in rows]
            finally:
                conn.close()

    def get_upcoming_events(
        self,
        limit: int = 10,
        timezone_id: Optional[str] = None,
        from_iso: Optional[str] = None,
    ) -> List[CalendarEventRead]:
        """Get the next upcoming meetings starting from current instant or from_iso."""
        if from_iso:
            try:
                _, from_ms, _ = parse_datetime_iso(from_iso, timezone_id or self._default_tz)
            except Exception:
                from_ms = int(time.time() * 1000)
        else:
            from_ms = int(time.time() * 1000)

        with _DB_LOCK:
            conn = get_db_connection(self._db_path)
            try:
                rows = conn.execute(
                    """
                    SELECT * FROM events
                    WHERE event_status NOT IN ('CANCELLED', 'DELETED')
                      AND end_utc > ?
                    ORDER BY start_utc ASC
                    LIMIT ?;
                    """,
                    (from_ms, limit),
                ).fetchall()
                return [self._row_to_event(r) for r in rows]
            finally:
                conn.close()

    def get_next_meeting(self, timezone_id: Optional[str] = None) -> Optional[CalendarEventRead]:
        """Fetch the immediate next upcoming meeting."""
        events = self.get_upcoming_events(limit=1, timezone_id=timezone_id)
        return events[0] if events else None

    def search_events_by_title(self, query: str, limit: int = 10) -> List[CalendarEventRead]:
        """Search calendar meetings by title keyword."""
        pattern = f"%{query.strip()}%"
        with _DB_LOCK:
            conn = get_db_connection(self._db_path)
            try:
                rows = conn.execute(
                    """
                    SELECT * FROM events
                    WHERE event_status NOT IN ('CANCELLED', 'DELETED')
                      AND title LIKE ?
                    ORDER BY start_utc DESC
                    LIMIT ?;
                    """,
                    (pattern, limit),
                ).fetchall()
                return [self._row_to_event(r) for r in rows]
            finally:
                conn.close()

    def get_calendar_summary(self, timezone_id: Optional[str] = None) -> Dict[str, Any]:
        """Return a structured summary of today's schedule and next meeting."""
        today_events = self.get_today_events(timezone_id)
        next_meeting = self.get_next_meeting(timezone_id)

        events_summary = []
        for e in today_events:
            s_dt = convert_utc_to_local(e.start_utc_ms, e.timezone_id)
            e_dt = convert_utc_to_local(e.end_utc_ms, e.timezone_id)
            events_summary.append({
                "id": e.id,
                "title": e.title,
                "time": f"{s_dt.strftime('%I:%M %p')} - {e_dt.strftime('%I:%M %p')}",
                "location": e.location,
            })

        next_summary = None
        if next_meeting:
            s_dt = convert_utc_to_local(next_meeting.start_utc_ms, next_meeting.timezone_id)
            next_summary = {
                "id": next_meeting.id,
                "title": next_meeting.title,
                "starts_at": s_dt.strftime("%A, %b %d at %I:%M %p"),
                "location": next_meeting.location,
            }

        return {
            "total_today": len(today_events),
            "today_schedule": events_summary,
            "next_meeting": next_summary,
        }
