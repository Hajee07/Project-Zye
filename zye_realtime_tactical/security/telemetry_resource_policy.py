"""
Telemetry Resource Policy.
Defines bounded computational budgets and memory constraints for
in-memory ring-buffer telemetry streams.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TelemetryResourcePolicy:
    """Resource constraints for telemetry buffers and stream concurrency."""

    # Default buffer capacity per stream
    DEFAULT_BUFFER_CAPACITY: int = 5000

    # Maximum configurable capacity per stream
    MAX_BUFFER_CAPACITY: int = 50000

    # Minimum configurable capacity per stream
    MIN_BUFFER_CAPACITY: int = 10

    # Maximum concurrent active streams
    MAX_ACTIVE_STREAMS: int = 100

    # Maximum batch size per ingestion call
    MAX_BATCH_SIZE: int = 1000

    # Maximum stream name length
    MAX_STREAM_NAME_LENGTH: int = 64

    # Idle stream cleanup threshold in seconds (e.g. 2 hours)
    IDLE_STREAM_EXPIRY_SECONDS: float = 7200.0

    # Minimum baseline samples required for statistical anomaly detection
    MIN_ANOMALY_BASELINE_SAMPLES: int = 10

    # Default Z-score anomaly threshold
    DEFAULT_ANOMALY_THRESHOLD: float = 2.5
