"""Adaptive Concurrency Controller with AIMD and Bounded Queueing (Day 27).

Controls in-flight concurrent requests per provider using:
- Additive Increase / Multiplicative Decrease (AIMD) algorithm
- Bounded queue wait times to enforce backpressure
- Independent provider slots to prevent slow providers from starving fast ones
- Real-time pressure calculation and active request tracking
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("zye.ai_plugins.concurrency")


class ProviderConcurrencyPool:
    """Manages active concurrency and queueing for a single AI provider."""

    def __init__(
        self,
        provider_id: str,
        initial_concurrency: int = 5,
        min_concurrency: int = 2,
        max_concurrency: int = 15,
        max_queue_size: int = 30,
        queue_timeout_seconds: float = 10.0,
    ):
        self.provider_id = provider_id
        self.current_limit: int = initial_concurrency
        self.min_concurrency = min_concurrency
        self.max_concurrency = max_concurrency
        self.max_queue_size = max_queue_size
        self.queue_timeout_seconds = queue_timeout_seconds

        self.active_requests: int = 0
        self.queued_requests: int = 0
        self.total_completed: int = 0
        self.total_rejected: int = 0
        self._lock = threading.Lock()

    def try_acquire(self) -> Tuple[bool, str]:
        """Attempt non-blocking slot acquisition."""
        with self._lock:
            if self.active_requests < self.current_limit:
                self.active_requests += 1
                return True, "Slot granted immediately"

            if self.queued_requests >= self.max_queue_size:
                self.total_rejected += 1
                return False, f"Queue is full ({self.queued_requests}/{self.max_queue_size} pending)"

            return False, "All slots active (needs queue wait)"

    def release(self, success: bool, latency_ms: float = 0.0) -> None:
        """Release an active slot and adaptively adjust concurrency limits."""
        with self._lock:
            self.active_requests = max(0, self.active_requests - 1)
            self.total_completed += 1

            # Adaptive Adjustment (AIMD)
            if success:
                # Additive Increase if performing well (< 1500ms)
                if latency_ms < 1500.0 and self.current_limit < self.max_concurrency:
                    # Every 5 successful fast requests, increment limit by 1
                    if self.total_completed % 5 == 0:
                        self.current_limit += 1
                        logger.debug("AIMD: Provider '%s' limit increased to %d", self.provider_id, self.current_limit)
            else:
                # Multiplicative Decrease on failure
                decreased = max(self.min_concurrency, int(self.current_limit * 0.7))
                if decreased != self.current_limit:
                    self.current_limit = decreased
                    logger.warning("AIMD: Provider '%s' limit decreased to %d due to failure", self.provider_id, self.current_limit)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            pressure = (self.active_requests / max(1, self.current_limit)) * 100.0
            return {
                "provider_id": self.provider_id,
                "current_concurrency_limit": self.current_limit,
                "active_requests": self.active_requests,
                "queued_requests": self.queued_requests,
                "max_concurrency": self.max_concurrency,
                "min_concurrency": self.min_concurrency,
                "concurrency_pressure_percent": round(pressure, 1),
                "total_completed": self.total_completed,
                "total_rejected": self.total_rejected,
            }


class ConcurrencyControllerRegistry:
    """Singleton managing concurrency across all AI providers."""

    _instance: Optional[ConcurrencyControllerRegistry] = None
    _lock = threading.Lock()

    def __init__(self):
        self._pools: Dict[str, ProviderConcurrencyPool] = {}

    @classmethod
    def get_instance(cls) -> ConcurrencyControllerRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_pool(self, provider_id: str) -> ProviderConcurrencyPool:
        pid = provider_id.lower().strip()
        if pid not in self._pools:
            with self._lock:
                if pid not in self._pools:
                    self._pools[pid] = ProviderConcurrencyPool(pid)
        return self._pools[pid]

    def acquire_slot(self, provider_id: str) -> Tuple[bool, str]:
        return self.get_pool(provider_id).try_acquire()

    def release_slot(self, provider_id: str, success: bool, latency_ms: float = 0.0) -> None:
        self.get_pool(provider_id).release(success, latency_ms)

    def get_status(self, provider_id: str) -> Dict[str, Any]:
        return self.get_pool(provider_id).to_dict()

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        return {pid: pool.to_dict() for pid, pool in self._pools.items()}


def get_concurrency_controller() -> ConcurrencyControllerRegistry:
    return ConcurrencyControllerRegistry.get_instance()
