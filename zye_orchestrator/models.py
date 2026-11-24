"""
Data models and schemas for Zye Master MCP Orchestrator (Day 15).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class ServerLifecycleState(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    RESTARTING = "RESTARTING"
    FAILED = "FAILED"
    SHUTTING_DOWN = "SHUTTING_DOWN"


class ToolRiskClass(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL_RISK = "CRITICAL_RISK"


class SafetyApprovalToken(BaseModel):
    token: str
    audit_id: str
    action: str
    target_resources: list[str] = Field(default_factory=list)
    issued_at: float
    expires_at: float
    user_confirmed: bool = False


class ServerHealthReport(BaseModel):
    server_name: str
    status: str
    session_active: bool
    generation: int = 0
    in_flight_calls: int = 0
    restart_count: int = 0
    last_error: str = ""
    last_health_check: str = ""
