"""
Calendar Management Engine for Zye Personal Assistant (Day 14 & Day 28).
Unified interface providing backward-compatible calendar operations backed by Day 28
transactional event engine, half-open interval conflict detection, and availability query engine.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import zoneinfo

from zye_personal_assistant.database import get_db_connection, init_assistant_database
from zye_personal_assistant.safety_gateway import SafetyGateway

from zye_personal_assistant.calendar.calendar_models import (
    CalendarEventCreate,
    CalendarEventUpdate,
    CalendarOperationResult,
)
from zye_personal_assistant.calendar.calendar_event_engine import CalendarEventEngine
from zye_personal_assistant.calendar.calendar_query_engine import CalendarQueryEngine
from zye_personal_assistant.calendar.calendar_availability_engine import find_free_time_slots
from zye_personal_assistant.calendar.calendar_conflict_engine import detect_interval_conflicts
from zye_personal_assistant.calendar.calendar_database import (
    initialize_calendar_database,
    verify_calendar_database_health,
)
from zye_personal_assistant.calendar.calendar_timezone_engine import (
    convert_local_to_utc,
    convert_utc_to_local,
    get_configured_timezone,
    parse_datetime_iso,
)

logger = logging.getLogger("zye.personal_assistant.calendar")


class CalendarEngine:
    """
    Unified Calendar Engine with Day 28 atomic transactions and half-open conflict checks.
    Fully backward-compatible with Day 14 callers.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        default_timezone: str = "Asia/Kolkata",
        safety_gateway: Optional[SafetyGateway] = None,
    ) -> None:
        self._db_path = db_path
        self._default_tz = get_configured_timezone(default_timezone)
        self._safety = safety_gateway or SafetyGateway(db_path=db_path)

        # Initialize Day 28 schema and engines
        initialize_calendar_database(self._db_path)
        self._event_engine = CalendarEventEngine(
            db_path=self._db_path,
            default_timezone=self._default_tz,
            safety_gateway=self._safety,
        )
        self._query_engine = CalendarQueryEngine(
            db_path=self._db_path,
            default_timezone=self._default_tz,
        )

    def check_conflicts(
        self,
        start_iso: str,
        end_iso: str,
        exclude_event_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Detect scheduling conflicts using standard half-open interval condition:
        existing.start < requested.end AND existing.end > requested.start.
        """
        try:
            _, start_utc_ms, _ = parse_datetime_iso(start_iso, self._default_tz)
            _, end_utc_ms, _ = parse_datetime_iso(end_iso, self._default_tz)
        except Exception as exc:
            return {
                "has_conflict": True,
                "conflict_count": 1,
                "conflicting_events": [],
                "error": str(exc),
                "recommended_alternative_slots": [],
            }

        conn = get_db_connection(self._db_path)
        try:
            rep = detect_interval_conflicts(
                conn=conn,
                start_utc_ms=start_utc_ms,
                end_utc_ms=end_utc_ms,
                exclude_event_id=exclude_event_id,
                timezone_id=self._default_tz,
            )
            alternatives = []
            if rep.has_conflict:
                start_local = convert_utc_to_local(start_utc_ms, self._default_tz)
                duration_mins = max(15, round((end_utc_ms - start_utc_ms) / 60000))
                alternatives = find_free_time_slots(
                    conn=conn,
                    target_date=start_local,
                    duration_minutes=duration_mins,
                    timezone_id=self._default_tz,
                    max_suggestions=3,
                )

            return {
                "has_conflict": rep.has_conflict,
                "conflict_count": rep.conflict_count,
                "conflicting_events": rep.conflicting_events,
                "recommended_alternative_slots": alternatives,
                "resolution_status": "CONFLICT_DETECTED" if rep.has_conflict else "CLEAR",
                "explanation": rep.explanation,
            }
        finally:
            conn.close()

    def add_event(
        self,
        title: str,
        start_iso: str,
        end_iso: str = "",
        location: str = "",
        notes: str = "",
        force_override: bool = False,
        operation_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a new calendar event with atomic conflict check and 15m/2m reminders.
        """
        create_payload = CalendarEventCreate(
            title=title,
            start_time=start_iso,
            end_time=end_iso if end_iso else None,
            location=location or "online",
            notes=notes or "",
            timezone_id=self._default_tz,
            operation_id=operation_id,
        )

        res = self._event_engine.create_event(create_payload, force_override=force_override)
        if res.status == "SUCCESS":
            return {
                "status": "SUCCESS",
                "event_id": res.event_id,
                "title": res.title,
                "start_iso": res.start_iso,
                "end_iso": res.end_iso,
                "location": location,
                "notes": notes,
                "reminders": res.reminders,
                "message": res.message,
            }
        elif res.status == "CONFLICT_BLOCKED":
            return {
                "status": "CONFLICT",
                "message": res.message,
                "conflicts": res.conflicts,
                "recommended_alternative_slots": res.suggested_slots,
            }
        else:
            return {
                "status": "ERROR",
                "message": res.message,
                "error_code": res.error_code,
            }

    def update_event(
        self,
        event_id: int,
        title: Optional[str] = None,
        start_iso: Optional[str] = None,
        end_iso: Optional[str] = None,
        location: Optional[str] = None,
        notes: Optional[str] = None,
        force_override: bool = False,
    ) -> dict[str, Any]:
        """Update meeting details with version bump and reminder refreshing."""
        payload = CalendarEventUpdate(
            event_id=event_id,
            title=title,
            start_time=start_iso,
            end_time=end_iso,
            location=location,
            notes=notes,
        )
        res = self._event_engine.update_event(payload, force_override=force_override)
        return res.to_dict()

    def reschedule_event(
        self,
        event_id: int,
        new_start_iso: str,
        new_duration_minutes: Optional[int] = None,
        force_override: bool = False,
    ) -> dict[str, Any]:
        """Reschedule meeting start time and duration."""
        res = self._event_engine.reschedule_event(
            event_id=event_id,
            new_start_time=new_start_iso,
            new_duration_minutes=new_duration_minutes,
            force_override=force_override,
        )
        return res.to_dict()

    def cancel_event(self, event_id: int) -> dict[str, Any]:
        """Soft-cancel an event and invalidate reminders."""
        res = self._event_engine.cancel_event(event_id)
        return res.to_dict()

    def delete_event(self, event_id: int) -> dict[str, Any]:
        """Permanently delete an event."""
        res = self._event_engine.delete_event(event_id, confirmed=True)
        return res.to_dict()

    def list_upcoming_events(self, limit: int = 15, from_iso: Optional[str] = None) -> list[dict[str, Any]]:
        """List upcoming scheduled events."""
        events = self._query_engine.get_upcoming_events(limit=limit, from_iso=from_iso)
        return [e.to_dict() for e in events]

    def get_daily_schedule(self, target_date_iso: Optional[str] = None) -> list[dict[str, Any]]:
        """Get events for today or specified target date."""
        if target_date_iso:
            try:
                target_dt, _, _ = parse_datetime_iso(target_date_iso, self._default_tz)
                events = self._query_engine.get_events_for_day(target_dt, self._default_tz)
            except Exception:
                events = self._query_engine.get_today_events(self._default_tz)
        else:
            events = self._query_engine.get_today_events(self._default_tz)
        return [e.to_dict() for e in events]

    def find_free_slots(
        self,
        target_date_iso: str,
        duration_minutes: int = 60,
        working_hours_start: str = "09:00",
        working_hours_end: str = "18:00",
    ) -> list[dict[str, str]]:
        """Find free time slots on a given day within working hours."""
        try:
            target_dt, _, _ = parse_datetime_iso(target_date_iso, self._default_tz)
        except Exception:
            target_dt = datetime.now(zoneinfo.ZoneInfo(self._default_tz))

        conn = get_db_connection(self._db_path)
        try:
            return find_free_time_slots(
                conn=conn,
                target_date=target_dt,
                duration_minutes=duration_minutes,
                working_hours_start=working_hours_start,
                working_hours_end=working_hours_end,
                timezone_id=self._default_tz,
            )
        finally:
            conn.close()

    def get_calendar_summary(self) -> dict[str, Any]:
        """Return daily summary and next meeting."""
        return self._query_engine.get_calendar_summary(self._default_tz)

    def get_calendar_health(self) -> dict[str, Any]:
        """Audit calendar database integrity and record metrics."""
        return verify_calendar_database_health(self._db_path)
