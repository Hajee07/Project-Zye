"""
Telemetry Data Models.
Strongly typed data representations for telemetry samples, stream configs, and timestamps.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TimestampSource(str, Enum):
    CALLER_PROVIDED = "CALLER_PROVIDED"
    LOCALLY_GENERATED_MONOTONIC = "LOCALLY_GENERATED_MONOTONIC"


class TelemetrySample(BaseModel):
    """Represents a single verified telemetry observation stored in the ring buffer."""
    value: float = Field(..., description="Numerical telemetry measurement (float64)")
    timestamp: float = Field(..., description="Timestamp in seconds")
    timestamp_source: TimestampSource = Field(default=TimestampSource.CALLER_PROVIDED)
    sequence_number: int = Field(..., description="Monotonically increasing ingestion index")
    received_at: float = Field(default_factory=time.time, description="Wall-clock receive timestamp")
    stream_name: str = Field(..., description="Associated stream identifier")


class StreamConfig(BaseModel):
    """Configuration parameters for a dedicated telemetry ring buffer."""
    stream_name: str = Field(..., description="Unique stream identifier")
    capacity: int = Field(default=5000, description="Maximum sample capacity (ring buffer size)")
    anomaly_threshold: float = Field(default=2.5, description="Z-score anomaly cutoff threshold")
    min_baseline_samples: int = Field(default=10, description="Minimum samples required before anomaly checks")


class StreamStatus(BaseModel):
    """Runtime status of an active telemetry stream."""
    stream_name: str
    capacity: int
    current_sample_count: int
    total_samples_ingested: int
    overwritten_samples: int
    first_sample_timestamp: Optional[float] = None
    last_sample_timestamp: Optional[float] = None
    last_activity_time: float
    timestamp_source: Optional[TimestampSource] = None
    created_at: float
    is_active: bool = True
