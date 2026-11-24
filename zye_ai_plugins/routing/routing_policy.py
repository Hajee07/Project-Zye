"""Routing Policy Definitions and Modes for Zye AI Multi-AI Hub (Day 27).

Defines the 9 official routing modes:
1. BALANCED: Balances reliability, quality, latency, and cost
2. QUALITY_FIRST: Prioritizes configured model capability and quality requirements
3. SPEED_FIRST: Prioritizes providers with suitable capabilities and lower observed latency
4. COST_FIRST: Prioritizes eligible lower-cost or free local providers
5. RELIABILITY_FIRST: Prioritizes providers with higher empirical availability and zero recent circuit trips
6. LOCAL_ONLY: Strictly restricts execution to local Ollama (100% offline air-gapped)
7. USER_SELECTED: Strictly respects the provider explicitly requested by the user
8. COUNCIL_MODE: Preserves exact multi-provider participant quorum for Day 26 Council
9. PRIVACY_RESTRICTED: Restricts external cloud egress based on data sensitivity
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zye.ai_plugins.routing_policy")

# Supported Routing Modes
MODE_BALANCED = "BALANCED"
MODE_QUALITY_FIRST = "QUALITY_FIRST"
MODE_SPEED_FIRST = "SPEED_FIRST"
MODE_COST_FIRST = "COST_FIRST"
MODE_RELIABILITY_FIRST = "RELIABILITY_FIRST"
MODE_LOCAL_ONLY = "LOCAL_ONLY"
MODE_USER_SELECTED = "USER_SELECTED"
MODE_COUNCIL_MODE = "COUNCIL_MODE"
MODE_PRIVACY_RESTRICTED = "PRIVACY_RESTRICTED"

ALL_ROUTING_MODES = [
    MODE_BALANCED,
    MODE_QUALITY_FIRST,
    MODE_SPEED_FIRST,
    MODE_COST_FIRST,
    MODE_RELIABILITY_FIRST,
    MODE_LOCAL_ONLY,
    MODE_USER_SELECTED,
    MODE_COUNCIL_MODE,
    MODE_PRIVACY_RESTRICTED,
]

# Mode weightings for candidate scoring: (quality_wt, speed_wt, cost_wt, reliability_wt)
MODE_WEIGHTS: Dict[str, Dict[str, float]] = {
    MODE_BALANCED: {"quality": 0.30, "speed": 0.25, "cost": 0.20, "reliability": 0.25},
    MODE_QUALITY_FIRST: {"quality": 0.60, "speed": 0.15, "cost": 0.05, "reliability": 0.20},
    MODE_SPEED_FIRST: {"quality": 0.15, "speed": 0.60, "cost": 0.10, "reliability": 0.15},
    MODE_COST_FIRST: {"quality": 0.15, "speed": 0.15, "cost": 0.55, "reliability": 0.15},
    MODE_RELIABILITY_FIRST: {"quality": 0.20, "speed": 0.10, "cost": 0.10, "reliability": 0.60},
}


def normalize_routing_mode(mode_str: Optional[str]) -> str:
    """Normalize input string to uppercase valid routing mode."""
    if not mode_str:
        return MODE_BALANCED

    clean = mode_str.upper().strip().replace("-", "_").replace(" ", "_")
    if clean in ALL_ROUTING_MODES:
        return clean

    # Aliases
    if clean in ("FAST", "SPEED", "LATENCY"):
        return MODE_SPEED_FIRST
    if clean in ("CHEAP", "LOW_COST", "ECONOMY", "COST"):
        return MODE_COST_FIRST
    if clean in ("QUALITY", "BEST", "SMART"):
        return MODE_QUALITY_FIRST
    if clean in ("LOCAL", "OFFLINE", "OLLAMA"):
        return MODE_LOCAL_ONLY
    if clean in ("RELIABLE", "STABLE", "SAFETY"):
        return MODE_RELIABILITY_FIRST
    if clean in ("COUNCIL", "DEBATE"):
        return MODE_COUNCIL_MODE
    if clean in ("PRIVATE", "PRIVACY"):
        return MODE_PRIVACY_RESTRICTED

    return MODE_BALANCED
