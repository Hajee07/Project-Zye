"""Provider Telemetry, Percentile Latency, and Reliability Ranking (Day 27).

Tracks rolling performance metrics across all AI providers:
- Rolling latency percentiles: P50, P90, P95, P99
- Success, failure, timeout, and throttle counts
- Mathematically grounded reliability scoring with sample-size confidence penalties
- Ranking explanation: Never treats a provider with 1 request as more reliable than one with 100 successful requests
"""

from __future__ import annotations

import logging
import math
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zye.ai_plugins.metrics")


class RollingLatencyTracker:
    """Tracks rolling latency observations and computes statistical percentiles."""

    def __init__(self, max_samples: int = 200):
        self.max_samples = max_samples
        self.samples: List[float] = []
        self._lock = threading.Lock()

    def record(self, latency_ms: float) -> None:
        if latency_ms <= 0:
            return
        with self._lock:
            self.samples.append(latency_ms)
            if len(self.samples) > self.max_samples:
                self.samples.pop(0)

    def get_percentiles(self) -> Dict[str, float]:
        with self._lock:
            if not self.samples:
                return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0, "avg": 0.0}

            sorted_samples = sorted(self.samples)
            n = len(sorted_samples)

            def _pct(p: float) -> float:
                idx = int(math.ceil(p * n) - 1)
                return sorted_samples[max(0, min(n - 1, idx))]

            return {
                "p50": round(_pct(0.50), 2),
                "p90": round(_pct(0.90), 2),
                "p95": round(_pct(0.95), 2),
                "p99": round(_pct(0.99), 2),
                "avg": round(sum(sorted_samples) / n, 2),
            }


class ProviderTelemetryRecord:
    """Telemetry data container for an individual provider."""

    def __init__(self, provider_id: str):
        self.provider_id = provider_id
        self.total_requests: int = 0
        self.successful_requests: int = 0
        self.failed_requests: int = 0
        self.timeout_requests: int = 0
        self.rate_limited_requests: int = 0
        self.latency_tracker = RollingLatencyTracker()
        self.first_recorded_time = time.time()
        self.last_recorded_time = time.time()
        self._lock = threading.Lock()

    def record_request(
        self,
        success: bool,
        latency_ms: float = 0.0,
        is_timeout: bool = False,
        is_rate_limited: bool = False,
    ) -> None:
        with self._lock:
            self.total_requests += 1
            self.last_recorded_time = time.time()

            if success:
                self.successful_requests += 1
                if latency_ms > 0:
                    self.latency_tracker.record(latency_ms)
            else:
                self.failed_requests += 1
                if is_timeout:
                    self.timeout_requests += 1
                if is_rate_limited:
                    self.rate_limited_requests += 1

    def calculate_reliability(self) -> Dict[str, Any]:
        with self._lock:
            total = self.total_requests
            if total == 0:
                return {
                    "provider_id": self.provider_id,
                    "reliability_score": 0.50,
                    "confidence_label": "NO_DATA",
                    "sample_size": 0,
                    "success_rate_percent": 0.0,
                    "message": "No requests recorded yet",
                }

            raw_success_rate = self.successful_requests / total
            timeout_penalty = (self.timeout_requests / total) * 0.3
            throttle_penalty = (self.rate_limited_requests / total) * 0.2

            base_score = max(0.0, raw_success_rate - timeout_penalty - throttle_penalty)

            # Sample size confidence damping
            # If total < 5, penalize score towards conservative mean (0.60)
            if total < 5:
                confidence_label = "LOW_SAMPLE_CONFIDENCE"
                damped_score = (base_score * 0.5) + (0.50 * 0.5)
            elif total < 15:
                confidence_label = "MODERATE_SAMPLE_CONFIDENCE"
                damped_score = (base_score * 0.8) + (0.50 * 0.2)
            else:
                confidence_label = "HIGH_SAMPLE_CONFIDENCE"
                damped_score = base_score

            pcts = self.latency_tracker.get_percentiles()

            return {
                "provider_id": self.provider_id,
                "reliability_score": round(damped_score, 3),
                "raw_score": round(base_score, 3),
                "confidence_label": confidence_label,
                "sample_size": total,
                "successful_count": self.successful_requests,
                "failed_count": self.failed_requests,
                "timeout_count": self.timeout_requests,
                "rate_limited_count": self.rate_limited_requests,
                "success_rate_percent": round(raw_success_rate * 100.0, 1),
                "p50_latency_ms": pcts["p50"],
                "p95_latency_ms": pcts["p95"],
                "avg_latency_ms": pcts["avg"],
            }


class TelemetryRegistry:
    """Singleton managing performance telemetry across all providers."""

    _instance: Optional[TelemetryRegistry] = None
    _lock = threading.Lock()

    def __init__(self):
        self._records: Dict[str, ProviderTelemetryRecord] = {}

    @classmethod
    def get_instance(cls) -> TelemetryRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_record(self, provider_id: str) -> ProviderTelemetryRecord:
        pid = provider_id.lower().strip()
        if pid not in self._records:
            with self._lock:
                if pid not in self._records:
                    self._records[pid] = ProviderTelemetryRecord(pid)
        return self._records[pid]

    def record_call(
        self,
        provider_id: str,
        success: bool,
        latency_ms: float = 0.0,
        is_timeout: bool = False,
        is_rate_limited: bool = False,
    ) -> None:
        self.get_record(provider_id).record_request(
            success=success,
            latency_ms=latency_ms,
            is_timeout=is_timeout,
            is_rate_limited=is_rate_limited,
        )

    def rank_providers_by_reliability(self) -> List[Dict[str, Any]]:
        """Rank all monitored providers by empirical reliability score."""
        scores = []
        for pid, record in self._records.items():
            scores.append(record.calculate_reliability())

        # Sort descending by reliability score, then ascending by p50 latency
        sorted_ranks = sorted(
            scores,
            key=lambda x: (x["reliability_score"], -x.get("p50_latency_ms", 9999)),
            reverse=True,
        )

        for rank_idx, entry in enumerate(sorted_ranks, 1):
            entry["rank"] = rank_idx

        return sorted_ranks


def get_telemetry_registry() -> TelemetryRegistry:
    return TelemetryRegistry.get_instance()
