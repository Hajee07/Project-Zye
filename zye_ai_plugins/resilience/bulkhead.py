"""Universal Bulkhead and Resilience Orchestrator for Zye AI (Day 27).

Wraps provider invocations with full bulkhead isolation:
- Circuit Breaker gatekeeping
- Rate Limit & Cooldown checks
- Concurrency limit allocation
- Exponential retry execution
- Failover event recording
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, TypeVar

from .circuit_breaker import get_circuit_breaker
from .concurrency_controller import get_concurrency_controller
from .rate_limiter import get_rate_limiter
from .retry_policy import execute_with_retry

logger = logging.getLogger("zye.ai_plugins.bulkhead")

T = TypeVar("T")


class FailoverEvent:
    """Record of a graceful provider failover event."""

    def __init__(
        self,
        original_provider: str,
        fallback_provider: str,
        reason: str,
        task_id: str = "",
        success: bool = True,
    ):
        self.timestamp = time.time()
        self.original_provider = original_provider
        self.fallback_provider = fallback_provider
        self.reason = reason
        self.task_id = task_id
        self.success = success

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "original_provider": self.original_provider,
            "fallback_provider": self.fallback_provider,
            "reason": self.reason,
            "task_id": self.task_id,
            "success": self.success,
        }


class BulkheadManager:
    """Orchestrates end-to-end resilience around AI calls."""

    _instance: Optional[BulkheadManager] = None

    def __init__(self):
        self.cb = get_circuit_breaker()
        self.rl = get_rate_limiter()
        self.cc = get_concurrency_controller()
        self._failover_history: List[FailoverEvent] = []

    @classmethod
    def get_instance(cls) -> BulkheadManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record_failover(
        self,
        original_provider: str,
        fallback_provider: str,
        reason: str,
        task_id: str = "",
        success: bool = True,
    ) -> None:
        """Log a provider failover occurrence."""
        ev = FailoverEvent(original_provider, fallback_provider, reason, task_id, success)
        self._failover_history.append(ev)
        # Keep last 100 failovers
        if len(self._failover_history) > 100:
            self._failover_history.pop(0)
        logger.info(
            "Failover recorded: '%s' -> '%s' (Reason: %s)",
            original_provider,
            fallback_provider,
            reason,
        )

    def get_failover_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent failover events."""
        return [ev.to_dict() for ev in reversed(self._failover_history[-limit:])]

    async def execute_call(
        self,
        provider_id: str,
        coro_fn: Callable[[], Coroutine[Any, Any, T]],
        estimated_tokens: int = 150,
        max_retries: int = 2,
    ) -> T:
        """Execute operation protected by rate limiter, circuit breaker, concurrency slot, and retry policy."""
        pid = provider_id.lower().strip()

        # 1. Circuit Breaker Check
        permitted, cb_reason = self.cb.check_permission(pid)
        if not permitted:
            raise RuntimeError(f"Circuit Breaker active for '{pid}': {cb_reason}")

        # 2. Rate Limiter Check
        can_proceed, wait_sec, rl_reason = self.rl.check_capacity(pid, estimated_tokens)
        if not can_proceed:
            if wait_sec > 5.0:
                raise RuntimeError(f"Rate Limiter blocked '{pid}': {rl_reason} (wait: {wait_sec}s)")
            await asyncio.sleep(wait_sec)

        # 3. Concurrency Slot Acquisition
        slot_acquired, cc_reason = self.cc.acquire_slot(pid)
        if not slot_acquired:
            raise RuntimeError(f"Concurrency Controller blocked '{pid}': {cc_reason}")

        start_time = time.monotonic()
        success = False
        try:
            # 4. Execute With Retry & Error Classification
            result = await execute_with_retry(
                provider_id=pid,
                operation_fn=coro_fn,
                max_retries=max_retries,
            )
            success = True
            return result
        finally:
            latency_ms = (time.monotonic() - start_time) * 1000.0
            self.cc.release_slot(pid, success=success, latency_ms=latency_ms)


def get_bulkhead_manager() -> BulkheadManager:
    return BulkheadManager.get_instance()
