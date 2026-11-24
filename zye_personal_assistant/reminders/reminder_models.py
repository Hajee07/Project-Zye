"""
Data Models for Persistent Meeting Reminders Subsystem (Day 28).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ReminderType(str, Enum):
    FIFTEEN_MIN = "15_MIN"
    TWO_MIN = "2_MIN"


class ReminderStatus(str, Enum):
    PENDING = "PENDING"
    CLAIMED = "CLAIMED"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    SUPPRESSED = "SUPPRESSED"
    CANCELLED = "CANCELLED"


class EventReminder(BaseModel):
    id: int
    event_id: int
    event_version: int = 1
    reminder_type: str
    offset_seconds: int
    due_at_utc: int  # UTC epoch milliseconds
    status: str = ReminderStatus.PENDING.value
    attempt_count: int = 0
    claimed_at_utc: Optional[int] = None
    delivered_at_utc: Optional[int] = None
    last_error_code: Optional[str] = None
    created_at_utc: int

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
