"""
Real-Time Meeting Conflict Detection & Atomic Overlap Prevention (Day 28).
Implements exact half-open interval overlap detection:
  existing.start < requested.end AND existing.end > requested.start
Meetings touching at exact boundaries are allowed (no conflict).
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from .calendar_models import ConflictReport
from .calendar_timezone_engine import convert_utc_to_local, format_event_time

logger = logging.getLogger("zye.personal_assistant.calendar.conflicts")


def detect_interval_conflicts(
    conn: sqlite3.Connection,
    start_utc_ms: int,
    end_utc_ms: int,
    exclude_event_id: Optional[int] = None,
    timezone_id: str = "Asia/Kolkata",
) -> ConflictReport:
    """
    Query database for any overlapping confirmed/scheduled meetings using half-open condition:
      existing.start_utc < requested_end_utc AND existing.end_utc > requested_start_utc
    """
    if end_utc_ms <= start_utc_ms:
        return ConflictReport(
            has_conflict=True,
            conflict_count=1,
            conflicting_events=[],
            suggested_slots=[],
            explanation="Invalid meeting interval: end time must be strictly after start time.",
        )

    query = """
        SELECT id, title, start_iso, end_iso, start_utc, end_utc, location, notes, timezone_id, event_status
        FROM events
        WHERE event_status NOT IN ('CANCELLED', 'DELETED')
          AND start_utc < ?
          AND end_utc > ?
    """
    params: list[Any] = [end_utc_ms, start_utc_ms]
    if exclude_event_id:
        query += " AND id != ?"
        params.append(exclude_event_id)

    query += " ORDER BY start_utc ASC;"

    rows = conn.execute(query, params).fetchall()
    conflicts: List[Dict[str, Any]] = []

    for r in rows:
        conflicts.append({
            "id": r["id"],
            "title": r["title"],
            "start_iso": r["start_iso"],
            "end_iso": r["end_iso"],
            "start_utc": r["start_utc"],
            "end_utc": r["end_utc"],
            "location": r["location"],
            "timezone_id": r["timezone_id"] or timezone_id,
        })

    has_conflict = len(conflicts) > 0

    if has_conflict:
        first = conflicts[0]
        s_dt = convert_utc_to_local(first["start_utc"], timezone_id)
        e_dt = convert_utc_to_local(first["end_utc"], timezone_id)
        s_str = s_dt.strftime("%I:%M %p")
        e_str = e_dt.strftime("%I:%M %p")
        explanation = (
            f"Conflict detected: '{first['title']}' is already scheduled from {s_str} to {e_str}. "
            f"Conflicting meeting booking has been blocked."
        )
    else:
        explanation = "No conflicts detected. Requested interval is clear."

    return ConflictReport(
        has_conflict=has_conflict,
        conflict_count=len(conflicts),
        conflicting_events=conflicts,
        suggested_slots=[],
        explanation=explanation,
    )


def validate_interval(start_utc_ms: int, end_utc_ms: int) -> Tuple[bool, str]:
    """Validate that interval is positive and bounded (5 minutes to 24 hours)."""
    if end_utc_ms <= start_utc_ms:
        return False, "Meeting end time must be strictly after start time."
    duration_ms = end_utc_ms - start_utc_ms
    min_ms = 5 * 60 * 1000
    max_ms = 24 * 60 * 60 * 1000
    if duration_ms < min_ms:
        return False, "Meeting duration must be at least 5 minutes."
    if duration_ms > max_ms:
        return False, "Meeting duration cannot exceed 24 hours."
    return True, "Valid"
