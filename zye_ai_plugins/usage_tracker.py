"""Thread-Safe AI Provider Usage Tracker and Telemetry for Zye AI.

Tracks token consumption, latency, call success/failure rates, and operational metrics
for all AI providers in the Multi-AI Plugin Hub.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

from .response_normalizer import AIUsage


class ProviderMetrics:
    """Metrics container for an individual AI provider."""

    def __init__(self, provider_id: str):
        self.provider_id = provider_id
        self.request_count: int = 0
        self.success_count: int = 0
        self.failure_count: int = 0
        self.timeout_count: int = 0
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.total_tokens: int = 0
        self.total_latency_ms: float = 0.0
        self.min_latency_ms: float = float("inf")
        self.max_latency_ms: float = 0.0
        self.last_used_at: Optional[float] = None
        self.last_error: Optional[str] = None

    def record(
        self,
        success: bool,
        usage: Optional[AIUsage] = None,
        is_timeout: bool = False,
        error: Optional[str] = None,
    ) -> None:
        self.request_count += 1
        self.last_used_at = time.time()

        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
            if is_timeout:
                self.timeout_count += 1
            if error:
                self.last_error = error

        if usage:
            self.prompt_tokens += usage.prompt_tokens
            self.completion_tokens += usage.completion_tokens
            self.total_tokens += usage.total_tokens

            if usage.latency_ms > 0:
                self.total_latency_ms += usage.latency_ms
                if usage.latency_ms < self.min_latency_ms:
                    self.min_latency_ms = usage.latency_ms
                if usage.latency_ms > self.max_latency_ms:
                    self.max_latency_ms = usage.latency_ms

    def to_dict(self) -> Dict[str, Any]:
        avg_latency = 0.0
        if self.request_count > 0 and self.total_latency_ms > 0:
            avg_latency = round(self.total_latency_ms / self.request_count, 2)

        min_lat = 0.0 if self.min_latency_ms == float("inf") else round(self.min_latency_ms, 2)

        return {
            "provider_id": self.provider_id,
            "request_count": self.request_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "timeout_count": self.timeout_count,
            "success_rate": round((self.success_count / self.request_count * 100), 2) if self.request_count > 0 else 100.0,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "avg_latency_ms": avg_latency,
            "min_latency_ms": min_lat,
            "max_latency_ms": round(self.max_latency_ms, 2),
            "last_used_timestamp": self.last_used_at,
            "last_error": self.last_error,
        }


class UsageTracker:
    """Global thread-safe usage tracker for AI plugins."""

    _instance: Optional["UsageTracker"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "UsageTracker":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._metrics: Dict[str, ProviderMetrics] = {}
                cls._instance._mutex = threading.Lock()
            return cls._instance

    def record_usage(
        self,
        provider_id: str,
        success: bool,
        usage: Optional[AIUsage] = None,
        is_timeout: bool = False,
        error: Optional[str] = None,
    ) -> None:
        """Record a single interaction with an AI provider."""
        with self._mutex:
            if provider_id not in self._metrics:
                self._metrics[provider_id] = ProviderMetrics(provider_id)
            self._metrics[provider_id].record(
                success=success,
                usage=usage,
                is_timeout=is_timeout,
                error=error,
            )

    def get_provider_usage(self, provider_id: str) -> Dict[str, Any]:
        """Get telemetry for a specific provider."""
        with self._mutex:
            if provider_id in self._metrics:
                return self._metrics[provider_id].to_dict()
            return ProviderMetrics(provider_id).to_dict()

    def get_all_usage(self) -> Dict[str, Any]:
        """Get aggregate metrics across all providers."""
        with self._mutex:
            providers_data = {pid: m.to_dict() for pid, m in self._metrics.items()}

            tot_req = sum(m.request_count for m in self._metrics.values())
            tot_succ = sum(m.success_count for m in self._metrics.values())
            tot_fail = sum(m.failure_count for m in self._metrics.values())
            tot_tokens = sum(m.total_tokens for m in self._metrics.values())

            return {
                "total_requests": tot_req,
                "total_success": tot_succ,
                "total_failures": tot_fail,
                "total_tokens_consumed": tot_tokens,
                "providers": providers_data,
            }

    def reset(self, provider_id: Optional[str] = None) -> None:
        """Reset metrics for one or all providers."""
        with self._mutex:
            if provider_id:
                if provider_id in self._metrics:
                    del self._metrics[provider_id]
            else:
                self._metrics.clear()


# Module-level singleton
usage_tracker = UsageTracker()
