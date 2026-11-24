"""
Opponent Buffer Manager Singleton (Day 36).
Provides centralized global access to OpponentSequenceManager and telemetry statistics.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from zye_realtime_tactical.opponent.opponent_sequence_manager import OpponentSequenceManager


class OpponentBufferManager:
    """Singleton holder for opponent sequence management and performance metrics."""

    _instance: Optional[OpponentBufferManager] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.sequence_manager = OpponentSequenceManager()
        self._total_predictions: int = 0
        self._total_compute_time_ms: float = 0.0
        self._metrics_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> OpponentBufferManager:
        """Returns the process-wide OpponentBufferManager singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Resets singleton state (for unit test isolation)."""
        with cls._lock:
            cls._instance = None

    def record_prediction(self, compute_time_ms: float) -> None:
        """Thread-safe update of prediction counts and latency."""
        with self._metrics_lock:
            self._total_predictions += 1
            self._total_compute_time_ms += compute_time_ms

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Returns aggregated opponent behaviour intelligence metrics."""
        with self._metrics_lock:
            total = self._total_predictions
            avg_latency = round(self._total_compute_time_ms / total, 4) if total > 0 else 0.0

        active_opponents = len(self.sequence_manager.list_opponents())
        total_actions_in_ram = sum(
            st.current_action_count for st in self.sequence_manager.list_opponents()
        )

        return {
            "total_predictions_executed": total,
            "average_compute_time_ms": avg_latency,
            "active_opponents_count": active_opponents,
            "total_actions_in_ram": total_actions_in_ram,
            "memory_storage_engine": "IN_MEMORY_COLLECTIONS_DEQUE",
            "zero_disk_latency": True,
        }
