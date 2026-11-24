"""
ZYE AI — Core Type Definitions & Execution Envelopes
===================================================

Defines:
- ZyeEventType: Full event taxonomy for Unified Event Bus (Section 06).
- ExecutionOutcome: Verified execution contract (Section 18).
- ResourceState: Resource governor states (Section 27).
- ModelCircuitState: Model failover states (Section 08-09).
- ZyeEvent: Structured, safe event envelope.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ZyeEventType(str, Enum):
    """Event categories required by Section 06 of Master Specification."""

    # Session lifecycle
    SESSION_STARTED = "SESSION_STARTED"
    SESSION_ENDED = "SESSION_ENDED"

    # Voice / user speech events
    USER_SPEECH_STARTED = "USER_SPEECH_STARTED"
    USER_TURN_ACCEPTED = "USER_TURN_ACCEPTED"
    USER_SPEECH_COMPLETED = "USER_SPEECH_COMPLETED"

    # Model intelligence events
    MODEL_REQUEST_STARTED = "MODEL_REQUEST_STARTED"
    MODEL_REQUEST_COMPLETED = "MODEL_REQUEST_COMPLETED"
    MODEL_REQUEST_FAILED = "MODEL_REQUEST_FAILED"
    MODEL_DEGRADED = "MODEL_DEGRADED"

    # Tool execution events
    TOOL_REQUESTED = "TOOL_REQUESTED"
    TOOL_EXECUTION_REQUESTED = "TOOL_REQUESTED"
    TOOL_EXECUTION_STARTED = "TOOL_EXECUTION_STARTED"
    TOOL_EXECUTION_COMPLETED = "TOOL_EXECUTION_COMPLETED"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"
    TOOL_EXECUTION_BLOCKED = "TOOL_EXECUTION_BLOCKED"
    TOOL_LOOP_DETECTED = "TOOL_LOOP_DETECTED"
    MODEL_CIRCUIT_TRIPPED = "MODEL_CIRCUIT_TRIPPED"

    # Memory events
    MEMORY_RETRIEVED = "MEMORY_RETRIEVED"
    MEMORY_UPDATED = "MEMORY_UPDATED"

    # Audio playback events
    AUDIO_PLAYBACK_STARTED = "AUDIO_PLAYBACK_STARTED"
    AUDIO_PLAYBACK_DRAINED = "AUDIO_PLAYBACK_DRAINED"

    # Security & governance events
    SECURITY_ALERT = "SECURITY_ALERT"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"

    # Autonomous task events
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"

    # Resource management events
    RESOURCE_PRESSURE = "RESOURCE_PRESSURE"
    SYSTEM_RECOVERED = "SYSTEM_RECOVERED"


class ExecutionOutcome(str, Enum):
    """Verified tool execution contract states (Section 18)."""
    REQUESTED = "REQUESTED"
    AUTHORIZED = "AUTHORIZED"
    STARTED = "STARTED"
    ACCEPTED_UNVERIFIED = "ACCEPTED_UNVERIFIED"
    VERIFIED_SUCCESS = "VERIFIED_SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PARTIAL = "PARTIAL"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    LOOP_BLOCKED = "LOOP_BLOCKED"
    CIRCUIT_BLOCKED = "CIRCUIT_BLOCKED"
    TIMED_OUT = "TIMED_OUT"
    DENIED = "DENIED"


class ResourceState(str, Enum):
    """Resource governor states (Section 27)."""
    NORMAL = "NORMAL"
    RESOURCE_PRESSURE = "RESOURCE_PRESSURE"
    HIGH_MEMORY_PRESSURE = "HIGH_MEMORY_PRESSURE"
    DEGRADED = "DEGRADED"
    RECOVERING = "RECOVERING"


class ModelCircuitState(str, Enum):
    """Circuit breaker states for model availability (Section 09)."""
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Tripped, requests blocked / diverted
    HALF_OPEN = "HALF_OPEN"  # Testing recovery with single probe


@dataclass
class ZyeEvent:
    """Safe, structured event envelope conforming to Section 06."""

    event_type: ZyeEventType
    source_module: str = "zye"
    payload: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    session_id: Optional[str] = None
    turn_id: Optional[str] = None
    task_id: Optional[str] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary, serializing Enum values."""
        d = asdict(self)
        d["event_type"] = self.event_type.value
        return d
