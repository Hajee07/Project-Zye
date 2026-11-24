"""
Telemetry Buffer Manager Singleton.
Global manager providing unified access to in-memory streams and performance metrics.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from zye_realtime_tactical.telemetry.telemetry_stream_manager import TelemetryStreamManager


class TelemetryBufferManager:
    """Singleton wrapper around TelemetryStreamManager with metrics tracking."""

    _instance: Optional[TelemetryBufferManager] = None
    _singleton_lock = threading.Lock()

    def __init__(self) -> None:
        self.stream_manager = TelemetryStreamManager()
        self.total_analyses_executed: int = 0
        self.total_errors_encountered: int = 0
        self.total_computation_time_ns: int = 0

    @classmethod
    def get_instance(cls) -> TelemetryBufferManager:
        """Thread-safe singleton accessor."""
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Resets singleton state (used in testing)."""
        with cls._singleton_lock:
            if cls._instance:
                cls._instance.stream_manager.clear_all()
                cls._instance.total_analyses_executed = 0
                cls._instance.total_errors_encountered = 0
                cls._instance.total_computation_time_ns = 0

    def record_analysis_metrics(self, duration_ns: int, is_error: bool = False) -> None:
        """Updates internal telemetry processing performance metrics."""
        self.total_analyses_executed += 1
        self.total_computation_time_ns += duration_ns
        if is_error:
            self.total_errors_encountered += 1

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Returns processing metrics across all streams."""
        avg_time_ms = 0.0
        if self.total_analyses_executed > 0:
            avg_time_ms = (self.total_computation_time_ns / self.total_analyses_executed) / 1_000_000.0

        active_streams = self.stream_manager.list_active_streams()
        total_samples = sum(s.current_sample_count for s in active_streams)
        total_overwritten = sum(s.overwritten_samples for s in active_streams)

        return {
            "total_analyses_executed": self.total_analyses_executed,
            "total_errors_encountered": self.total_errors_encountered,
            "average_compute_time_ms": round(avg_time_ms, 4),
            "active_streams_count": len(active_streams),
            "total_samples_in_memory": total_samples,
            "total_samples_overwritten": total_overwritten,
        }
