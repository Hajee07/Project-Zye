"""
Unit tests for ZYE Resource Governor, Local Readiness Detector, and Hybrid Model Router.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from zye_core.event_bus import ZyeEventBus
from zye_core.types import ModelCircuitState, ResourceState, ZyeEventType
from zye_intelligence.circuit_breaker import ModelCircuitBreaker
from zye_intelligence.hybrid_router import HybridModelRouter
from zye_intelligence.local_readiness import LocalReadinessDetector
from zye_reliability.resource_governor import (
    ResourceGovernor,
    ResourceGovernorConfig,
    SystemMetrics,
)


def test_resource_governor_hysteresis_state_machine():
    config = ResourceGovernorConfig(
        memory_pressure_percent=80.0,
        high_memory_pressure_percent=88.0,
        recovery_clear_percent=78.0,
    )
    governor = ResourceGovernor(config=config)

    # 1. Normal state (70%)
    s1 = governor._evaluate_state(ram_percent=70.0, cpu_percent=10.0, current_state=ResourceState.NORMAL)
    assert s1 == ResourceState.NORMAL

    # 2. Resource pressure (82%)
    s2 = governor._evaluate_state(ram_percent=82.0, cpu_percent=10.0, current_state=ResourceState.NORMAL)
    assert s2 == ResourceState.RESOURCE_PRESSURE

    # 3. High memory pressure (89%)
    s3 = governor._evaluate_state(ram_percent=89.0, cpu_percent=10.0, current_state=ResourceState.RESOURCE_PRESSURE)
    assert s3 == ResourceState.HIGH_MEMORY_PRESSURE

    # 4. Drops to 84% - because previous was HIGH_MEMORY_PRESSURE and > 78%, remains RECOVERING
    s4 = governor._evaluate_state(ram_percent=84.0, cpu_percent=10.0, current_state=ResourceState.HIGH_MEMORY_PRESSURE)
    assert s4 == ResourceState.RESOURCE_PRESSURE or s4 == ResourceState.RECOVERING

    # 5. Drops below 78% (e.g. 75%) -> returns to NORMAL
    s5 = governor._evaluate_state(ram_percent=75.0, cpu_percent=10.0, current_state=ResourceState.RECOVERING)
    assert s5 == ResourceState.NORMAL


def test_resource_governor_blocks_local_inference_at_high_pressure():
    governor = ResourceGovernor()
    governor.sample_metrics = MagicMock(
        return_value=SystemMetrics(
            ram_percent=91.0,
            ram_available_mb=500.0,
            ram_total_mb=16000.0,
            cpu_percent=15.0,
            disk_percent=40.0,
            state=ResourceState.HIGH_MEMORY_PRESSURE,
            timestamp=100.0,
        )
    )

    allowed, reason = governor.is_local_inference_permitted()
    assert allowed is False
    assert "exceeds" in reason or "rejected" in reason.lower()


def test_local_readiness_fails_closed_under_memory_pressure():
    governor = ResourceGovernor()
    governor.sample_metrics = MagicMock(
        return_value=SystemMetrics(
            ram_percent=92.0,
            ram_available_mb=300.0,
            ram_total_mb=16000.0,
            cpu_percent=10.0,
            disk_percent=50.0,
            state=ResourceState.HIGH_MEMORY_PRESSURE,
            timestamp=100.0,
        )
    )

    detector = LocalReadinessDetector(governor=governor)
    profile = detector.evaluate_readiness()
    assert profile.is_ready_for_local_inference is False
    assert "REJECTED" in profile.status_reason


def test_hybrid_router_selects_gemini_and_handles_circuit_failover():
    cb = ModelCircuitBreaker(default_failure_threshold=2, default_cooldown_seconds=10.0)
    router = HybridModelRouter(circuit_breaker=cb)

    # Normal routing to Gemini Pro
    v1 = router.route_request("Explain quantum entanglement in detail", requires_deep_reasoning=True)
    assert v1.selected_model == "gemini-2.5-pro"
    assert v1.is_local is False

    # Trip Gemini Pro circuit
    cb.record_transient_failure("gemini-2.5-pro")
    cb.record_transient_failure("gemini-2.5-pro")
    assert cb.allow_request("gemini-2.5-pro") is False

    # Route again -> failover to gemini-2.5-flash
    v2 = router.route_request("Explain quantum entanglement in detail", requires_deep_reasoning=True)
    assert v2.selected_model == "gemini-2.5-flash"
    assert "Failing over" in v2.rationale
