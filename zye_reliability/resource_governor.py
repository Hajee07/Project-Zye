"""
ZYE AI — Dynamic Resource Governor & System Health Monitor
==========================================================

Implements Section 27 of Master Engineering Specification.
Monitors host OS memory, CPU, and disk saturation.
Enforces:
1. Strict hysteresis on memory pressure (triggers at 88% memory, recovers below 78%).
2. Rejection of local model inference and heavy background workers under HIGH_MEMORY_PRESSURE.
3. Event bus emissions on resource state transitions (RESOURCE_PRESSURE, SYSTEM_RECOVERED).
4. Safe fallback for machines without psutil or elevated hardware access.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from zye_core.event_bus import ZyeEventBus
from zye_core.types import ResourceState, ZyeEvent, ZyeEventType

logger = logging.getLogger("zye.reliability.resource_governor")

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


@dataclass(slots=True)
class ResourceGovernorConfig:
    """Configurable thresholds for Resource Governor."""

    memory_pressure_percent: float = 80.0
    high_memory_pressure_percent: float = 88.0
    recovery_clear_percent: float = 78.0
    cpu_saturation_percent: float = 90.0
    disk_full_threshold_percent: float = 95.0
    sample_interval_seconds: float = 5.0


@dataclass(slots=True)
class SystemMetrics:
    """Snapshot of current system host resource utilization."""

    ram_percent: float
    ram_available_mb: float
    ram_total_mb: float
    cpu_percent: float
    disk_percent: float
    state: ResourceState
    timestamp: float


class ResourceGovernor:
    """
    Continuous resource monitor and admission gate for memory-intensive operations.
    Enforces strict hysteresis to prevent thrashing.
    """

    def __init__(
        self,
        config: Optional[ResourceGovernorConfig] = None,
        event_bus: Optional[ZyeEventBus] = None,
    ) -> None:
        self.config = config or ResourceGovernorConfig()
        self.event_bus = event_bus
        self._current_state = ResourceState.NORMAL
        self._last_metrics: Optional[SystemMetrics] = None
        self._lock = threading.Lock()

    def sample_metrics(self) -> SystemMetrics:
        """Poll host metrics and determine current ResourceState with hysteresis."""
        with self._lock:
            now = time.time()
            if _HAS_PSUTIL:
                try:
                    mem = psutil.virtual_memory()
                    cpu = psutil.cpu_percent(interval=None)
                    import os
                    drive = os.path.splitdrive(os.getcwd())[0] or "C:"
                    disk = psutil.disk_usage(f"{drive}\\").percent
                    ram_percent = mem.percent
                    ram_available_mb = mem.available / (1024 * 1024)
                    ram_total_mb = mem.total / (1024 * 1024)
                except Exception as exc:
                    logger.warning("Failed to query psutil metrics: %s", exc)
                    ram_percent = 50.0
                    ram_available_mb = 4096.0
                    ram_total_mb = 8192.0
                    cpu = 10.0
                    disk = 50.0
            else:
                ram_percent = 50.0
                ram_available_mb = 4096.0
                ram_total_mb = 8192.0
                cpu = 10.0
                disk = 50.0

            prior_state = self._current_state
            new_state = self._evaluate_state(ram_percent, cpu, prior_state)

            metrics = SystemMetrics(
                ram_percent=ram_percent,
                ram_available_mb=ram_available_mb,
                ram_total_mb=ram_total_mb,
                cpu_percent=cpu,
                disk_percent=disk,
                state=new_state,
                timestamp=now,
            )
            self._last_metrics = metrics
            self._current_state = new_state

            if new_state != prior_state:
                self._handle_state_transition(prior_state, new_state, metrics)

            return metrics

    def _evaluate_state(
        self,
        ram_percent: float,
        cpu_percent: float,
        current_state: ResourceState,
    ) -> ResourceState:
        """Apply hysteresis state machine logic."""
        # 1. Critical High Memory Pressure (> 88%)
        if ram_percent >= self.config.high_memory_pressure_percent:
            return ResourceState.HIGH_MEMORY_PRESSURE

        # 2. Memory Pressure (>= 80%)
        if ram_percent >= self.config.memory_pressure_percent:
            return ResourceState.RESOURCE_PRESSURE

        # 3. CPU Saturation
        if cpu_percent >= self.config.cpu_saturation_percent:
            return ResourceState.DEGRADED

        # 4. Hysteresis Recovery: If previously under pressure, only clear below 78%
        if current_state in (ResourceState.HIGH_MEMORY_PRESSURE, ResourceState.RESOURCE_PRESSURE):
            if ram_percent < self.config.recovery_clear_percent:
                return ResourceState.NORMAL
            else:
                return ResourceState.RECOVERING

        return ResourceState.NORMAL

    def _handle_state_transition(
        self,
        old_state: ResourceState,
        new_state: ResourceState,
        metrics: SystemMetrics,
    ) -> None:
        """Notify event bus of resource state escalation or recovery."""
        logger.info(
            "Resource Governor transition: %s -> %s (RAM: %0.1f%%, CPU: %0.1f%%)",
            old_state.value,
            new_state.value,
            metrics.ram_percent,
            metrics.cpu_percent,
        )

        if not self.event_bus:
            return

        if new_state in (ResourceState.RESOURCE_PRESSURE, ResourceState.HIGH_MEMORY_PRESSURE):
            self.event_bus.publish_sync(
                ZyeEvent(
                    event_type=ZyeEventType.RESOURCE_PRESSURE,
                    source_module="zye.reliability.resource_governor",
                    payload={
                        "old_state": old_state.value,
                        "new_state": new_state.value,
                        "ram_percent": metrics.ram_percent,
                        "ram_available_mb": metrics.ram_available_mb,
                        "cpu_percent": metrics.cpu_percent,
                    },
                )
            )
        elif new_state == ResourceState.NORMAL and old_state != ResourceState.NORMAL:
            self.event_bus.publish_sync(
                ZyeEvent(
                    event_type=ZyeEventType.SYSTEM_RECOVERED,
                    source_module="zye.reliability.resource_governor",
                    payload={
                        "ram_percent": metrics.ram_percent,
                        "ram_available_mb": metrics.ram_available_mb,
                        "state": new_state.value,
                    },
                )
            )

    def is_local_inference_permitted(self) -> Tuple[bool, str]:
        """
        Gate check for local LLM execution.
        Strictly forbids local model loading when RAM exceeds high_memory_pressure_percent (88%).
        """
        metrics = self.sample_metrics()
        if metrics.state == ResourceState.HIGH_MEMORY_PRESSURE:
            reason = (
                f"Local model inference rejected: Host RAM is {metrics.ram_percent:0.1f}% "
                f"(exceeds {self.config.high_memory_pressure_percent}% limit). "
                f"Falling back to Gemini Master Brain."
            )
            return False, reason

        if metrics.state == ResourceState.RESOURCE_PRESSURE:
            reason = (
                f"Resource pressure detected ({metrics.ram_percent:0.1f}% RAM). "
                f"Local model inference deferred to preserve system stability."
            )
            return False, reason

        return True, "Resource headroom acceptable for local execution."

    def can_allocate_memory_mb(self, required_mb: float) -> bool:
        """Determine if required memory buffer can be safely allocated."""
        metrics = self.sample_metrics()
        return (metrics.ram_available_mb - required_mb) > 1024.0


__all__ = [
    "ResourceGovernorConfig",
    "SystemMetrics",
    "ResourceGovernor",
]
