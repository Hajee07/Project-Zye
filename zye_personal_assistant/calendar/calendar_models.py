"""
Pydantic Data Models for Zye Smart Calendar Engine (Day 28).
Provides strict validation for event creation, updates, conflict checks, and queries.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class CalendarEventCreate(BaseModel):
    """Input payload for scheduling a new calendar event."""
    title: str = Field(..., min_length=1, max_length=200, description="Meeting title or objective")
    start_time: str = Field(..., description="Start datetime in ISO format or natural date-time string")
    end_time: Optional[str] = Field(default="", description="End datetime in ISO format (optional)")
    duration_minutes: int = Field(default=60, ge=5, le=1440, description="Duration in minutes if end_time omitted")
    timezone_id: str = Field(default="Asia/Kolkata", description="IANA Timezone Identifier")
    location: str = Field(default="online", max_length=200, description="Meeting location or platform")
    notes: str = Field(default="", max_length=2000, description="Agenda or meeting notes")
    operation_id: Optional[str] = Field(default=None, description="Client idempotency key to prevent duplicates")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Meeting title cannot be empty or whitespace only.")
        return clean


class CalendarEventUpdate(BaseModel):
    """Input payload for modifying an existing calendar event."""
    event_id: int = Field(..., gt=0, description="Target event ID to update")
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    start_time: Optional[str] = Field(default=None, description="New start datetime")
    end_time: Optional[str] = Field(default=None, description="New end datetime")
    duration_minutes: Optional[int] = Field(default=None, ge=5, le=1440)
    timezone_id: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = Field(default=None, max_length=2000)
    expected_version: Optional[int] = Field(default=None, description="Optimistic concurrency control version")


class CalendarEventDelete(BaseModel):
    """Input payload for deleting or cancelling an event."""
    event_id: int = Field(..., gt=0, description="Target event ID")
    confirmed: bool = Field(default=False, description="Explicit confirmation for permanent deletion")
    soft_cancel_only: bool = Field(default=True, description="Whether to soft-cancel rather than hard delete")


class CalendarEventRead(BaseModel):
    """Normalized structured representation of a stored calendar event."""
    id: int
    title: str
    start_iso: str
    end_iso: str
    start_utc_ms: int
    end_utc_ms: int
    timezone_id: str
    location: str = ""
    notes: str = ""
    event_status: str = "SCHEDULED"  # SCHEDULED | CONFIRMED | CANCELLED | COMPLETED
    version: int = 1
    reminded_15m: int = 0
    reminded_2m: int = 0
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class CalendarConflictCheck(BaseModel):
    """Parameters for checking interval overlap."""
    start_iso: str
    end_iso: str
    timezone_id: str = "Asia/Kolkata"
    exclude_event_id: Optional[int] = None


class ConflictReport(BaseModel):
    """Result of real-time conflict inspection."""
    has_conflict: bool
    conflict_count: int = 0
    conflicting_events: List[Dict[str, Any]] = Field(default_factory=list)
    suggested_slots: List[Dict[str, Any]] = Field(default_factory=list)
    explanation: str = "No conflicts detected."


class CalendarAvailabilityQuery(BaseModel):
    """Parameters for discovering free time slots."""
    target_date_iso: str
    duration_minutes: int = 60
    working_hours_start: str = "09:00"
    working_hours_end: str = "18:00"
    min_gap_minutes: int = 0
    timezone_id: str = "Asia/Kolkata"
    max_suggestions: int = 5


class CalendarOperationResult(BaseModel):
    """Standardized result returned by calendar engine operations."""
    status: str  # SUCCESS | CONFLICT_BLOCKED | ERROR | CANCELLED | NOT_FOUND
    event_id: Optional[int] = None
    title: Optional[str] = None
    start_iso: Optional[str] = None
    end_iso: Optional[str] = None
    timezone_id: Optional[str] = None
    reminders: List[Dict[str, Any]] = Field(default_factory=list)
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    suggested_slots: List[Dict[str, Any]] = Field(default_factory=list)
    message: str = ""
    error_code: Optional[str] = None
    trace_id: str = Field(default_factory=lambda: f"cal_{uuid.uuid4().hex[:8]}")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
