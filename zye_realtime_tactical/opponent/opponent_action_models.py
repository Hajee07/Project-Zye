"""
Opponent Action Data Models.
Represents individual observed actions, stream configuration, and opponent runtime status.
"""

from __future__ import annotations

import time
from typing import List, Optional
from pydantic import BaseModel, Field

from zye_realtime_tactical.telemetry.telemetry_models import TimestampSource


class OpponentAction(BaseModel):
    """Represents a single verified action event recorded for an opponent."""
    opponent_id: str = Field(default="", description="Unique opponent or agent identifier")
    action: str = Field(..., description="Original raw action label")
    normalized_action: str = Field(default="", description="Canonical lowercase stripped action label")
    timestamp: float = Field(default_factory=time.time, description="Timestamp in seconds")
    timestamp_source: TimestampSource = Field(default=TimestampSource.CALLER_PROVIDED)
    sequence_number: int = Field(default=0, description="Monotonically increasing sequence index")
    received_at: float = Field(default_factory=time.time, description="Local wall-clock receive timestamp")

    def model_post_init(self, __context: object) -> None:
        if not self.normalized_action and self.action:
            self.normalized_action = self.action.strip().casefold()


class OpponentSequenceConfig(BaseModel):
    """Configuration for an opponent's bounded sequence buffer."""
    opponent_id: str = Field(default="default", description="Opponent identifier")
    capacity: int = Field(default=1000, description="Maximum sequence buffer capacity (default: 1,000)")
    max_buffer_capacity: int = Field(default=1000, description="Max buffer capacity alias")
    min_observations: int = Field(default=6, description="Minimum actions required before prediction")
    min_context_support: int = Field(default=2, description="Minimum transitions needed for 2nd-order Markov")


class OpponentStatus(BaseModel):
    """Runtime status of an opponent's tracked action sequence."""
    opponent_id: str
    capacity: int
    current_action_count: int
    total_actions_observed: int
    total_ingested_actions: int = 0
    overwritten_actions: int = 0
    first_action_timestamp: Optional[float] = None
    last_action_timestamp: Optional[float] = None
    last_action: Optional[str] = None
    current_state: Optional[str] = None
    last_activity_time: float = Field(default_factory=time.time)
    timestamp_source: Optional[TimestampSource] = None
    created_at: float = Field(default_factory=time.time)
    is_active: bool = True

    def model_post_init(self, __context: object) -> None:
        if not self.total_ingested_actions and self.total_actions_observed:
            self.total_ingested_actions = self.total_actions_observed
