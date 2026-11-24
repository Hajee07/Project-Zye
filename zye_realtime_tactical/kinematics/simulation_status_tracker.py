"""
Simulation Status & Runtime Performance Tracker (Day 37 / Phase 3).
Maintains real-time telemetry metrics on kinematic simulations, execution latency,
active analysis jobs, and last completed job snapshots.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

from zye_realtime_tactical.kinematics.kinematic_models import MonteCarloResult


class SimulationStatusTracker:
    """Singleton tracker for kinematic risk and Monte Carlo simulation metrics."""

    _instance: Optional[SimulationStatusTracker] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._total_simulations: int = 0
        self._total_deterministic_analyses: int = 0
        self._total_scenarios_simulated: int = 0
        self._total_compute_time_ms: float = 0.0
        self._active_jobs: int = 0
        self._error_count: int = 0
        self._last_completed_result: Optional[Dict[str, Any]] = None
        self._last_completed_timestamp: float = 0.0
        self._started_at: float = time.time()

    @classmethod
    def get_instance(cls) -> SimulationStatusTracker:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def record_job_start(self) -> None:
        with self._lock:
            self._active_jobs += 1

    def record_job_end(self, result: Optional[MonteCarloResult] = None, compute_time_ms: float = 0.0) -> None:
        with self._lock:
            self._active_jobs = max(0, self._active_jobs - 1)
            self._total_simulations += 1
            self._total_compute_time_ms += compute_time_ms
            if result:
                self._total_scenarios_simulated += result.sample_count
                self._last_completed_result = {
                    "scenario_id": result.scenario_id,
                    "sample_count": result.sample_count,
                    "collision_probability": result.collision_probability,
                    "risk_category": result.risk_category.value,
                    "execution_time_ms": result.execution_time_ms,
                }
                self._last_completed_timestamp = time.time()

    def record_deterministic_analysis(self, compute_time_ms: float) -> None:
        with self._lock:
            self._total_deterministic_analyses += 1
            self._total_compute_time_ms += compute_time_ms

    def record_error(self) -> None:
        with self._lock:
            self._active_jobs = max(0, self._active_jobs - 1)
            self._error_count += 1

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            avg_time = (
                round(self._total_compute_time_ms / self._total_simulations, 3)
                if self._total_simulations > 0
                else 0.0
            )
            return {
                "engine_status": "OPERATIONAL",
                "uptime_seconds": round(time.time() - self._started_at, 1),
                "active_jobs": self._active_jobs,
                "total_simulations": self._total_simulations,
                "total_deterministic_analyses": self._total_deterministic_analyses,
                "total_scenarios_simulated": self._total_scenarios_simulated,
                "average_simulation_time_ms": avg_time,
                "error_count": self._error_count,
                "last_completed_job": self._last_completed_result,
                "last_completed_timestamp": self._last_completed_timestamp,
            }

    def reset(self) -> None:
        """Reset internal metrics (primarily for test suite isolation)."""
        with self._lock:
            self._total_simulations = 0
            self._total_deterministic_analyses = 0
            self._total_scenarios_simulated = 0
            self._total_compute_time_ms = 0.0
            self._active_jobs = 0
            self._error_count = 0
            self._last_completed_result = None
            self._last_completed_timestamp = 0.0
