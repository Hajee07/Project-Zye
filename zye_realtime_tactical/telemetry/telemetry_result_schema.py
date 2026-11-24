"""
Telemetry Result Schemas.
Structured Pydantic output models for real-time telemetry analysis and anomaly detection.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnomalyStatus(str, Enum):
    NORMAL = "NORMAL"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    INSUFFICIENT_BASELINE = "INSUFFICIENT_BASELINE"
    ZERO_VARIANCE_BASELINE = "ZERO_VARIANCE_BASELINE"
    INVALID_STATISTICS = "INVALID_STATISTICS"


class TelemetryAnalysisResult(BaseModel):
    """Complete structured output returned by analyze_realtime_stream."""
    status: str = Field(default="SUCCESS", description="SUCCESS or ERROR")
    stream: str = Field(..., description="Stream name analyzed")
    sample_count: int = Field(..., description="Number of samples in current analysis window")
    total_samples_ingested: int = Field(..., description="Lifetime samples ingested for this stream")
    overwritten_samples: int = Field(..., description="Count of historical samples discarded by ring buffer rollover")
    current_value: Optional[float] = Field(default=None, description="Latest numerical telemetry value")
    rolling_mean: Optional[float] = Field(default=None, description="Rolling mean across current window")
    std_dev: Optional[float] = Field(default=None, description="Rolling population/sample standard deviation")
    min_value: Optional[float] = Field(default=None, description="Minimum value in current window")
    max_value: Optional[float] = Field(default=None, description="Maximum value in current window")
    rate_of_change_per_sec: Optional[float] = Field(default=None, description="First derivative: instantaneous velocity (units/sec)")
    acceleration_per_sec2: Optional[float] = Field(default=None, description="Second derivative: acceleration (units/sec^2)")
    anomaly_z_score: Optional[float] = Field(default=None, description="Z-score relative to historical baseline")
    is_anomaly: bool = Field(default=False, description="True if anomaly_status is ANOMALY_DETECTED")
    anomaly_status: AnomalyStatus = Field(default=AnomalyStatus.INSUFFICIENT_BASELINE)
    anomaly_threshold: float = Field(default=2.5, description="Z-score threshold configured for this stream")
    baseline_sample_count: int = Field(default=0, description="Count of historical baseline samples used for anomaly test")
    baseline_mean: Optional[float] = Field(default=None, description="Historical baseline mean (excluding current sample)")
    baseline_std_dev: Optional[float] = Field(default=None, description="Historical baseline standard deviation")
    timestamp_source: str = Field(default="CALLER_PROVIDED", description="CALLER_PROVIDED or LOCALLY_GENERATED_MONOTONIC")
    compute_time_ms: float = Field(default=0.0, description="Numerical computation duration in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Error message if status is ERROR")
