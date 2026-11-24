"""Telemetry and Analytics Subsystem for Zye AI (Day 27).

Exports:
- Cost Estimator and Rate Card Lookup
- Provider Health State Machine
- Percentile Latencies and Reliability Ranking
"""

from .cost_estimator import (
    calculate_actual_cost,
    compare_provider_costs,
    estimate_request_cost,
    lookup_model_pricing,
)
from .provider_health import (
    HEALTH_AUTH_FAILED,
    HEALTH_AVAILABLE,
    HEALTH_CIRCUIT_OPEN,
    HEALTH_CONFIGURED,
    HEALTH_DEGRADED,
    HEALTH_DISABLED,
    HEALTH_RATE_LIMITED,
    HEALTH_UNKNOWN,
    check_provider_health,
    compute_health_state,
    inspect_all_provider_health,
)
from .provider_metrics import (
    ProviderTelemetryRecord,
    RollingLatencyTracker,
    TelemetryRegistry,
    get_telemetry_registry,
)

__all__ = [
    "lookup_model_pricing",
    "estimate_request_cost",
    "calculate_actual_cost",
    "compare_provider_costs",
    "HEALTH_CONFIGURED",
    "HEALTH_AVAILABLE",
    "HEALTH_DEGRADED",
    "HEALTH_RATE_LIMITED",
    "HEALTH_CIRCUIT_OPEN",
    "HEALTH_AUTH_FAILED",
    "HEALTH_DISABLED",
    "HEALTH_UNKNOWN",
    "compute_health_state",
    "check_provider_health",
    "inspect_all_provider_health",
    "RollingLatencyTracker",
    "ProviderTelemetryRecord",
    "TelemetryRegistry",
    "get_telemetry_registry",
]
