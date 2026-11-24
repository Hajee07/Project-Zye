"""
Data models and schemas for Zye Personal Assistant & Daily Management Core (Day 14).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class Priority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ProjectStatus(str, Enum):
    ACTIVE = "ACTIVE"
    AT_RISK = "AT_RISK"
    COMPLETED = "COMPLETED"
    ON_HOLD = "ON_HOLD"


class EmailAction(str, Enum):
    FETCH_UNREAD = "fetch_unread"
    DRAFT = "draft"
    SEND = "send"


class CalendarAction(str, Enum):
    ADD = "add"
    LIST_UPCOMING = "list_upcoming"
    CHECK_CONFLICTS = "check_conflicts"
    DELETE = "delete"
    DAILY_SCHEDULE = "daily_schedule"
    WEEKLY_SCHEDULE = "weekly_schedule"
    FIND_FREE_TIME = "find_free_time"


class DocumentAction(str, Enum):
    INDEX_FOLDER = "index_folder"
    SEARCH = "search"
    AUTO_ORGANIZE = "auto_organize"


class TaskAction(str, Enum):
    ADD = "add"
    LIST = "list"
    COMPLETE = "complete"
    AUTO_TIMEBLOCK_TODAY = "auto_timeblock_today"


class ProjectAction(str, Enum):
    CREATE_OR_UPDATE = "create_or_update"
    FLAG_BLOCKER = "flag_blocker"
    STATUS_BOARD = "status_board"


class CalendarEvent(BaseModel):
    id: Optional[int] = None
    title: str
    start_iso: str
    end_iso: str
    location: str = ""
    notes: str = ""
    reminded_15m: int = 0
    reminded_2m: int = 0
    timezone: str = "Asia/Kolkata"
    event_status: str = "SCHEDULED"
    reminder_state: str = "PENDING"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AssistantTask(BaseModel):
    id: Optional[int] = None
    title: str
    priority: Priority = Priority.MEDIUM
    due_iso: str = ""
    est_minutes: int = 30
    project_name: str = "General"
    status: TaskStatus = TaskStatus.PENDING
    scheduled_start_iso: str = ""
    scheduled_end_iso: str = ""
    linked_event_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AssistantProject(BaseModel):
    id: Optional[int] = None
    name: str
    objective: str = ""
    deadline_iso: str = ""
    status: ProjectStatus = ProjectStatus.ACTIVE
    blockers: str = ""
    completion_percent: float = 0.0
    risk_level: str = "LOW"
    owner: str = "User"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DocumentRecord(BaseModel):
    path: str
    filename: str
    category: str
    modified_at: str
    snippet: str = ""
    file_size: int = 0
    content_hash: str = ""
    indexed_at: Optional[str] = None
    processing_status: str = "INDEXED"


class EmailDraft(BaseModel):
    id: Optional[int] = None
    to_addr: str
    subject: str
    body: str
    attachments: list[str] = Field(default_factory=list)
    tone: str = "Professional"
    created_at: Optional[str] = None
    status: str = "DRAFT"


class TravelItinerary(BaseModel):
    destination: str
    days: int
    purpose: str
    budget_tier: str
    itinerary: list[dict[str, Any]] = Field(default_factory=list)
    estimated_costs: dict[str, float] = Field(default_factory=dict)
    packing_checklist: list[str] = Field(default_factory=list)
    risks_and_mitigation: list[dict[str, str]] = Field(default_factory=list)
    is_live_verified: bool = False
