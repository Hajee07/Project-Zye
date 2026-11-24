"""Intelligent AI Provider Routing Subsystem for Zye AI (Day 27).

Exports:
- Routing Policy Modes (BALANCED, QUALITY_FIRST, SPEED_FIRST, COST_FIRST, RELIABILITY_FIRST, LOCAL_ONLY, USER_SELECTED, COUNCIL_MODE, PRIVACY_RESTRICTED)
- Provider Router & Explainable Routing Decision
- Fallback Provider Selector
"""

from .provider_router import (
    RoutingDecision,
    calculate_routing_score,
    select_best_provider,
    select_fallback_provider,
)
from .routing_policy import (
    ALL_ROUTING_MODES,
    MODE_BALANCED,
    MODE_COST_FIRST,
    MODE_COUNCIL_MODE,
    MODE_LOCAL_ONLY,
    MODE_PRIVACY_RESTRICTED,
    MODE_QUALITY_FIRST,
    MODE_RELIABILITY_FIRST,
    MODE_SPEED_FIRST,
    MODE_USER_SELECTED,
    MODE_WEIGHTS,
    normalize_routing_mode,
)

__all__ = [
    "ALL_ROUTING_MODES",
    "MODE_BALANCED",
    "MODE_QUALITY_FIRST",
    "MODE_SPEED_FIRST",
    "MODE_COST_FIRST",
    "MODE_RELIABILITY_FIRST",
    "MODE_LOCAL_ONLY",
    "MODE_USER_SELECTED",
    "MODE_COUNCIL_MODE",
    "MODE_PRIVACY_RESTRICTED",
    "MODE_WEIGHTS",
    "normalize_routing_mode",
    "RoutingDecision",
    "calculate_routing_score",
    "select_best_provider",
    "select_fallback_provider",
]
