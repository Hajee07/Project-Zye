"""
Advanced Calendar Event Engine (Day 28).
Provides atomic event creation, interval validation, race-free conflict prevention (BEGIN IMMEDIATE),
event rescheduling, soft cancellation, duplicate prevention, and persistent reminder generation.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from zye_personal_assistant.database import _DB_LOCK, get_db_connection
from zye_personal_assistant.safety_gateway import SafetyGateway
from zye_personal_assistant.reminders.reminder_repository import (
    cancel_reminders_for_event,
    create_reminders_for_event,
    get_reminders_for_event,
)

from .calendar_availability_engine import suggest_alternative_slots
from .calendar_conflict_engine import detect_interval_conflicts, validate_interval
from .calendar_database import atomic_calendar_transaction, initialize_calendar_database
from .calendar_models import (
    CalendarEventCreate,
    CalendarEventRead,
    CalendarEventUpdate,
    CalendarOperationResult,
)
from .calendar_timezone_engine import (
    convert_local_to_utc,
    convert_utc_to_local,
    format_event_time,
    get_configured_timezone,
    parse_datetime_iso,
)

logger = logging.getLogger("zye.personal_assistant.calendar.events")


class CalendarEventEngine:
    """Core calendar event engine governing transactional operations and audits."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        default_timezone: str = "Asia/Kolkata",
        safety_gateway: Optional[SafetyGateway] = None,
        default_tz: Optional[str] = None,
    ) -> None:
        self._db_path = db_path
        self._default_tz = get_configured_timezone(default_tz or default_timezone)
        self._safety = safety_gateway or SafetyGateway(db_path=db_path)
        initialize_calendar_database(self._db_path)

    def create_event(self, payload: CalendarEventCreate, force_override: bool = False) -> CalendarOperationResult:
        """
        Schedule a new calendar event with atomic conflict detection (BEGIN IMMEDIATE).
        If an overlap is detected, blocks creation and provides available alternatives.
        """
        tz_name = get_configured_timezone(payload.timezone_id or self._default_tz)

        # 1. Parse start time
        try:
            start_local, start_utc_ms, start_norm_iso = parse_datetime_iso(payload.start_time, tz_name)
        except Exception as exc:
            return CalendarOperationResult(
                status="ERROR",
                message=f"Invalid start datetime: {exc}",
                error_code="CALENDAR_EVENT_INVALID_START",
            )

        # 2. Parse end time or apply duration
        if payload.end_time and payload.end_time.strip():
            try:
                end_local, end_utc_ms, end_norm_iso = parse_datetime_iso(payload.end_time, tz_name)
            except Exception as exc:
                return CalendarOperationResult(
                    status="ERROR",
                    message=f"Invalid end datetime: {exc}",
                    error_code="CALENDAR_EVENT_INVALID_END",
                )
        else:
            duration_delta = timedelta(minutes=payload.duration_minutes)
            end_local = start_local + duration_delta
            end_utc_ms, _ = convert_local_to_utc(end_local, tz_name)
            end_norm_iso = end_local.isoformat()

        # 3. Validate interval
        valid_int, int_err = validate_interval(start_utc_ms, end_utc_ms)
        if not valid_int:
            return CalendarOperationResult(
                status="ERROR",
                message=int_err,
                error_code="CALENDAR_EVENT_INVALID_INTERVAL",
            )

        now_ms = int(time.time() * 1000)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Day 13 Negative Pre-Mortem Brain Audit (Pre-flight prior to lock acquisition)
        try:
            self._safety.authorize_personal_assistant_action_sync(
                action_type="CALENDAR_CREATE_EVENT",
                task_description=f"Schedule calendar event: {payload.title}",
                proposed_steps=[
                    f"Verify timezone {tz_name}",
                    f"Check conflicts",
                    f"Persist event '{payload.title}' from {start_norm_iso} to {end_norm_iso}",
                ],
                target_resources=[f"calendar:event:{payload.title}"],
            )
        except Exception as e:
            logger.debug("Safety gateway audit notice: %s", e)

        # 4. Atomic Transaction: Check Idempotency + Conflicts + Insert Event + Reminders
        with _DB_LOCK:
            with atomic_calendar_transaction(self._db_path) as conn:
                # Idempotency check: Operation ID or identical duplicate
                if payload.operation_id and payload.operation_id.strip():
                    existing_op = conn.execute(
                        "SELECT id, title, start_iso, end_iso FROM events WHERE operation_id = ? AND event_status != 'CANCELLED';",
                        (payload.operation_id.strip(),),
                    ).fetchone()
                    if existing_op:
                        logger.info("Idempotent request detected for op_id '%s'", payload.operation_id)
                        return CalendarOperationResult(
                            status="SUCCESS",
                            event_id=existing_op["id"],
                            title=existing_op["title"],
                            start_iso=existing_op["start_iso"],
                            end_iso=existing_op["end_iso"],
                            timezone_id=tz_name,
                            message=f"Event already scheduled (idempotent match for op_id '{payload.operation_id}').",
                        )

                # Duplicate detection: exact title and start time
                dup_row = conn.execute(
                    "SELECT id FROM events WHERE title = ? AND start_utc = ? AND event_status NOT IN ('CANCELLED', 'DELETED');",
                    (payload.title, start_utc_ms),
                ).fetchone()
                if dup_row:
                    return CalendarOperationResult(
                        status="ERROR",
                        event_id=dup_row["id"],
                        message=f"Duplicate meeting detected: '{payload.title}' is already scheduled at this time.",
                        error_code="CALENDAR_EVENT_DUPLICATE",
                    )

                # Conflict Detection
                conflict_report = detect_interval_conflicts(
                    conn=conn,
                    start_utc_ms=start_utc_ms,
                    end_utc_ms=end_utc_ms,
                    timezone_id=tz_name,
                )

                if conflict_report.has_conflict and not force_override:
                    suggested = suggest_alternative_slots(
                        conn=conn,
                        requested_start_utc_ms=start_utc_ms,
                        duration_minutes=payload.duration_minutes,
                        timezone_id=tz_name,
                        max_suggestions=3,
                    )
                    return CalendarOperationResult(
                        status="CONFLICT_BLOCKED",
                        conflicts=conflict_report.conflicting_events,
                        suggested_slots=suggested,
                        message=conflict_report.explanation,
                        error_code="CALENDAR_CONFLICT",
                    )

                # Insert Event
                cursor = conn.execute(
                    """
                    INSERT INTO events
                    (title, start_iso, end_iso, start_utc, end_utc, location, notes,
                     reminded_15m, reminded_2m, timezone, timezone_id, version,
                     source, operation_id, created_at, updated_at, event_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, 1, 'voice', ?, ?, ?, 'SCHEDULED');
                    """,
                    (
                        payload.title,
                        start_norm_iso,
                        end_norm_iso,
                        start_utc_ms,
                        end_utc_ms,
                        payload.location,
                        payload.notes,
                        tz_name,
                        tz_name,
                        payload.operation_id or "",
                        now_iso,
                        now_iso,
                    ),
                )
                event_id = cursor.lastrowid

                # Generate 15m and 2m persistent reminders
                reminders = create_reminders_for_event(
                    conn=conn,
                    event_id=event_id,
                    event_version=1,
                    start_utc_ms=start_utc_ms,
                    created_at_utc_ms=now_ms,
                )

        logger.info("Successfully created calendar event id=%d: '%s'", event_id, payload.title)
        return CalendarOperationResult(
            status="SUCCESS",
            event_id=event_id,
            title=payload.title,
            start_iso=start_norm_iso,
            end_iso=end_norm_iso,
            timezone_id=tz_name,
            reminders=reminders,
            message=f"Meeting '{payload.title}' successfully scheduled for {format_event_time(start_local, tz_name)}.",
        )

    def get_event(self, event_id: int) -> Optional[CalendarEventRead]:
        """Fetch event record by primary key."""
        with _DB_LOCK:
            conn = get_db_connection(self._db_path)
            try:
                row = conn.execute("SELECT * FROM events WHERE id = ?;", (event_id,)).fetchone()
                if not row:
                    return None
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
            finally:
                conn.close()

    def update_event(self, payload: CalendarEventUpdate, force_override: bool = False) -> CalendarOperationResult:
        """Update meeting details, adjusting start/end times and refreshing reminders."""
        with _DB_LOCK:
            with atomic_calendar_transaction(self._db_path) as conn:
                row = conn.execute("SELECT * FROM events WHERE id = ?;", (payload.event_id,)).fetchone()
                if not row:
                    return CalendarOperationResult(
                        status="NOT_FOUND",
                        error_code="CALENDAR_EVENT_NOT_FOUND",
                        message=f"Event id {payload.event_id} does not exist.",
                    )

                if row["event_status"] == "CANCELLED":
                    return CalendarOperationResult(
                        status="ERROR",
                        error_code="CALENDAR_EVENT_CANCELLED",
                        message="Cannot update a cancelled event.",
                    )

                current_version = row["version"] or 1
                if payload.expected_version and payload.expected_version != current_version:
                    return CalendarOperationResult(
                        status="ERROR",
                        error_code="CALENDAR_EVENT_VERSION_CONFLICT",
                        message=f"Optimistic lock conflict: version {payload.expected_version} does not match {current_version}.",
                    )

                tz_name = get_configured_timezone(payload.timezone_id or row["timezone_id"] or self._default_tz)
                new_title = payload.title.strip() if payload.title else row["title"]
                new_location = payload.location if payload.location is not None else row["location"]
                new_notes = payload.notes if payload.notes is not None else row["notes"]

                time_changed = False
                if payload.start_time:
                    start_local, start_utc_ms, start_norm_iso = parse_datetime_iso(payload.start_time, tz_name)
                    time_changed = True
                else:
                    start_utc_ms = row["start_utc"]
                    start_norm_iso = row["start_iso"]
                    start_local = convert_utc_to_local(start_utc_ms, tz_name)

                if payload.end_time:
                    end_local, end_utc_ms, end_norm_iso = parse_datetime_iso(payload.end_time, tz_name)
                    time_changed = True
                elif payload.duration_minutes:
                    end_local = start_local + timedelta(minutes=payload.duration_minutes)
                    end_utc_ms, _ = convert_local_to_utc(end_local, tz_name)
                    end_norm_iso = end_local.isoformat()
                    time_changed = True
                else:
                    end_utc_ms = row["end_utc"]
                    end_norm_iso = row["end_iso"]

                if time_changed:
                    valid_int, int_err = validate_interval(start_utc_ms, end_utc_ms)
                    if not valid_int:
                        return CalendarOperationResult(
                            status="ERROR",
                            message=int_err,
                            error_code="CALENDAR_EVENT_INVALID_INTERVAL",
                        )

                    # Conflict Check excluding self
                    conflict_report = detect_interval_conflicts(
                        conn=conn,
                        start_utc_ms=start_utc_ms,
                        end_utc_ms=end_utc_ms,
                        exclude_event_id=payload.event_id,
                        timezone_id=tz_name,
                    )

                    if conflict_report.has_conflict and not force_override:
                        duration_mins = max(15, round((end_utc_ms - start_utc_ms) / 60000))
                        suggested = suggest_alternative_slots(
                            conn=conn,
                            requested_start_utc_ms=start_utc_ms,
                            duration_minutes=duration_mins,
                            timezone_id=tz_name,
                        )
                        return CalendarOperationResult(
                            status="CONFLICT_BLOCKED",
                            conflicts=conflict_report.conflicting_events,
                            suggested_slots=suggested,
                            message=conflict_report.explanation,
                            error_code="CALENDAR_CONFLICT",
                        )

                new_version = current_version + 1
                now_iso = datetime.now(timezone.utc).isoformat()
                now_ms = int(time.time() * 1000)

                conn.execute(
                    """
                    UPDATE events
                    SET title = ?, start_iso = ?, end_iso = ?, start_utc = ?, end_utc = ?,
                        location = ?, notes = ?, timezone_id = ?, version = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (
                        new_title,
                        start_norm_iso,
                        end_norm_iso,
                        start_utc_ms,
                        end_utc_ms,
                        new_location,
                        new_notes,
                        tz_name,
                        new_version,
                        now_iso,
                        payload.event_id,
                    ),
                )

                reminders = []
                if time_changed:
                    # Invalidate old reminders and create fresh ones for the new version
                    cancel_reminders_for_event(conn, payload.event_id)
                    reminders = create_reminders_for_event(
                        conn=conn,
                        event_id=payload.event_id,
                        event_version=new_version,
                        start_utc_ms=start_utc_ms,
                        created_at_utc_ms=now_ms,
                    )

        logger.info("Updated event id=%d: version=%d", payload.event_id, new_version)
        return CalendarOperationResult(
            status="SUCCESS",
            event_id=payload.event_id,
            title=new_title,
            start_iso=start_norm_iso,
            end_iso=end_norm_iso,
            timezone_id=tz_name,
            reminders=reminders,
            message=f"Meeting '{new_title}' successfully updated.",
        )

    def reschedule_event(
        self,
        event_id: int,
        new_start_time: Optional[str] = None,
        new_duration_minutes: Optional[int] = None,
        force_override: bool = False,
        new_start_iso: Optional[str] = None,
    ) -> CalendarOperationResult:
        """Move a meeting to a new time."""
        effective_start = new_start_iso or new_start_time
        if not effective_start:
            return CalendarOperationResult(
                status="ERROR",
                error_code="CALENDAR_INVALID_INPUT",
                message="Either new_start_time or new_start_iso must be provided.",
            )
        return self.update_event(
            CalendarEventUpdate(
                event_id=event_id,
                start_time=effective_start,
                duration_minutes=new_duration_minutes,
            ),
            force_override=force_override,
        )

    def cancel_event(self, event_id: int) -> CalendarOperationResult:
        """Soft-cancel meeting and cancel all pending reminders."""
        with _DB_LOCK:
            with atomic_calendar_transaction(self._db_path) as conn:
                row = conn.execute("SELECT id, title FROM events WHERE id = ?;", (event_id,)).fetchone()
                if not row:
                    return CalendarOperationResult(status="NOT_FOUND", message=f"Event {event_id} not found.")

                conn.execute(
                    "UPDATE events SET event_status = 'CANCELLED', updated_at = ? WHERE id = ?;",
                    (datetime.now(timezone.utc).isoformat(), event_id),
                )
                cancel_reminders_for_event(conn, event_id)

        logger.info("Cancelled event id=%d: '%s'", event_id, row["title"])
        return CalendarOperationResult(
            status="CANCELLED",
            event_id=event_id,
            title=row["title"],
            message=f"Meeting '{row['title']}' has been cancelled.",
        )

    def delete_event(self, event_id: int, confirmed: bool = False) -> CalendarOperationResult:
        """Permanently delete an event record."""
        if not confirmed:
            return CalendarOperationResult(
                status="ERROR",
                error_code="CONFIRMATION_REQUIRED",
                message="Permanent deletion requires confirmed=True.",
            )

        with _DB_LOCK:
            with atomic_calendar_transaction(self._db_path) as conn:
                row = conn.execute("SELECT id, title FROM events WHERE id = ?;", (event_id,)).fetchone()
                if not row:
                    return CalendarOperationResult(status="NOT_FOUND", message=f"Event {event_id} not found.")

                cancel_reminders_for_event(conn, event_id)
                conn.execute("DELETE FROM events WHERE id = ?;", (event_id,))

        logger.info("Permanently deleted event id=%d", event_id)
        return CalendarOperationResult(
            status="SUCCESS",
            event_id=event_id,
            message=f"Meeting id {event_id} permanently deleted.",
        )
