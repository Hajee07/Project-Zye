"""
Intelligent Free-Slot Recommendation & Calendar Availability Engine (Day 28).
Finds non-conflicting time slots within working hours, respecting meeting duration,
minimum buffer gaps, and avoiding past times.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union
import zoneinfo

from .calendar_conflict_engine import detect_interval_conflicts
from .calendar_timezone_engine import (
    convert_local_to_utc,
    convert_utc_to_local,
    get_current_local_datetime,
    get_zone_info,
)

logger = logging.getLogger("zye.personal_assistant.calendar.availability")


def find_free_time_slots(
    conn: sqlite3.Connection,
    target_date: Optional[Union[datetime, str]] = None,
    duration_minutes: int = 60,
    working_hours_start: str = "09:00",
    working_hours_end: str = "18:00",
    min_gap_minutes: int = 0,
    timezone_id: str = "Asia/Kolkata",
    max_suggestions: int = 5,
    target_date_iso: Optional[str] = None,
    work_start_hour: Optional[int] = None,
    work_end_hour: Optional[int] = None,
    min_slot_minutes: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Scan a target date for free blocks that can accommodate duration_minutes.
    Excludes past times, respect working hours and minimum meeting gaps.
    """
    effective_target = target_date_iso or target_date or datetime.now()
    if isinstance(effective_target, str):
        if "T" in effective_target:
            target_date_obj = datetime.fromisoformat(effective_target)
        else:
            parts = [int(p) for p in effective_target.split("-")]
            target_date_obj = datetime(parts[0], parts[1], parts[2], 0, 0, 0)
    else:
        target_date_obj = effective_target

    eff_duration = min_slot_minutes or duration_minutes

    if work_start_hour is not None:
        working_hours_start = f"{work_start_hour:02d}:00"
    if work_end_hour is not None:
        working_hours_end = f"{work_end_hour:02d}:00"

    tz = get_zone_info(timezone_id)
    target_local = target_date_obj.astimezone(tz) if target_date_obj.tzinfo else target_date_obj.replace(tzinfo=tz)
    now_local = datetime.now(tz)

    # Parse working hours on target day
    try:
        sh, sm = map(int, working_hours_start.split(":"))
        eh, em = map(int, working_hours_end.split(":"))
    except Exception:
        sh, sm = 9, 0
        eh, em = 18, 0

    day_start = target_local.replace(hour=sh, minute=sm, second=0, microsecond=0)
    day_end = target_local.replace(hour=eh, minute=em, second=0, microsecond=0)

    # If target day is today, advance day_start past current time + 5 min buffer
    if target_local.date() == now_local.date() and day_start < now_local:
        # Round up to next 15-minute mark
        rem = 15 - (now_local.minute % 15)
        day_start = (now_local + timedelta(minutes=rem)).replace(second=0, microsecond=0)

    if day_start >= day_end:
        return []

    day_start_ms, _ = convert_local_to_utc(day_start, timezone_id)
    day_end_ms, _ = convert_local_to_utc(day_end, timezone_id)

    # Fetch all non-cancelled events on that day
    query = """
        SELECT start_utc, end_utc
        FROM events
        WHERE event_status NOT IN ('CANCELLED', 'DELETED')
          AND start_utc < ?
          AND end_utc > ?
        ORDER BY start_utc ASC;
    """
    rows = conn.execute(query, (day_end_ms, day_start_ms)).fetchall()
    busy_intervals: List[tuple[int, int]] = [(r["start_utc"], r["end_utc"]) for r in rows]

    duration_ms = eff_duration * 60 * 1000
    gap_ms = min_gap_minutes * 60 * 1000

    suggestions: List[Dict[str, str]] = []
    cursor_ms = day_start_ms

    for b_start, b_end in busy_intervals:
        if cursor_ms + duration_ms <= b_start:
            # We found a slot before this busy interval!
            slot_end_ms = cursor_ms + duration_ms
            _add_slot_suggestion(suggestions, cursor_ms, slot_end_ms, timezone_id)
            if len(suggestions) >= max_suggestions:
                return suggestions

        # Move cursor to end of busy interval + optional gap
        if b_end + gap_ms > cursor_ms:
            cursor_ms = b_end + gap_ms

    # Check remaining time after the last busy block up to day_end
    while cursor_ms + duration_ms <= day_end_ms and len(suggestions) < max_suggestions:
        slot_end_ms = cursor_ms + duration_ms
        _add_slot_suggestion(suggestions, cursor_ms, slot_end_ms, timezone_id)
        cursor_ms = slot_end_ms + gap_ms

    return suggestions


def _add_slot_suggestion(
    suggestions: List[Dict[str, Any]],
    start_ms: int,
    end_ms: int,
    timezone_id: str,
) -> None:
    s_dt = convert_utc_to_local(start_ms, timezone_id)
    e_dt = convert_utc_to_local(end_ms, timezone_id)
    suggestions.append({
        "start_iso": s_dt.isoformat(),
        "end_iso": e_dt.isoformat(),
        "slot_label": f"{s_dt.strftime('%I:%M %p')} - {e_dt.strftime('%I:%M %p')}",
        "date_label": s_dt.strftime("%A, %b %d"),
        "duration_minutes": int(round((end_ms - start_ms) / 60000.0)),
    })


def suggest_alternative_slots(
    conn: sqlite3.Connection,
    requested_start_utc_ms: int,
    duration_minutes: int,
    timezone_id: str = "Asia/Kolkata",
    max_suggestions: int = 3,
) -> List[Dict[str, str]]:
    """Suggest alternative slots following a detected conflict."""
    start_local = convert_utc_to_local(requested_start_utc_ms, timezone_id)
    alternatives = find_free_time_slots(
        conn=conn,
        target_date=start_local,
        duration_minutes=duration_minutes,
        timezone_id=timezone_id,
        max_suggestions=max_suggestions,
    )

    # If none found today, check tomorrow
    if len(alternatives) < max_suggestions:
        next_day = start_local + timedelta(days=1)
        next_day_alts = find_free_time_slots(
            conn=conn,
            target_date=next_day,
            duration_minutes=duration_minutes,
            timezone_id=timezone_id,
            max_suggestions=max_suggestions - len(alternatives),
        )
        alternatives.extend(next_day_alts)

    return alternatives
