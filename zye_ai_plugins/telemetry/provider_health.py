"""Enterprise Provider Health Monitor and Diagnostics (Day 27).

Evaluates the health and availability of all AI providers:
- Formal Health State Taxonomy:
  * CONFIGURED: Config exists but not yet pinged
  * AVAILABLE: Fully operational and responding to pings
  * DEGRADED: Responding with elevated latency or intermittent errors
  * RATE_LIMITED: Currently throttled or in rate-limit cooldown
  * CIRCUIT_OPEN: Blocked by active circuit breaker trips
  * AUTH_FAILED: Invalid API key or permission denied
  * DISABLED: Explicitly turned off in configuration
  * UNKNOWN: Uninitialized or unmonitored
- Non-billable passive and active lightweight probing
- Clear separation between Configuration Health, Transport Health, and Model Availability
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..resilience.circuit_breaker import STATE_OPEN, get_circuit_breaker
from ..resilience.rate_limiter import get_rate_limiter

logger = logging.getLogger("zye.ai_plugins.health")

HEALTH_CONFIGURED = "CONFIGURED"
HEALTH_AVAILABLE = "AVAILABLE"
HEALTH_DEGRADED = "DEGRADED"
HEALTH_RATE_LIMITED = "RATE_LIMITED"
HEALTH_CIRCUIT_OPEN = "CIRCUIT_OPEN"
HEALTH_AUTH_FAILED = "AUTH_FAILED"
HEALTH_DISABLED = "DISABLED"
HEALTH_UNKNOWN = "UNKNOWN"


def compute_health_state(
    provider_id: str,
    is_enabled: bool,
    is_configured: bool,
    circuit_state: str,
    in_cooldown: bool,
    last_error: Optional[str] = None,
    consecutive_failures: int = 0,
) -> str:
    """Determine the authoritative health state for a provider."""
    if not is_enabled:
        return HEALTH_DISABLED

    if not is_configured:
        return HEALTH_CONFIGURED

    if circuit_state == STATE_OPEN:
        return HEALTH_CIRCUIT_OPEN

    if in_cooldown:
        return HEALTH_RATE_LIMITED

    if last_error and any(k in last_error.lower() for k in ("unauthorized", "invalid_api_key", "auth", "forbidden")):
        return HEALTH_AUTH_FAILED

    if consecutive_failures > 0:
        return HEALTH_DEGRADED

    return HEALTH_AVAILABLE


async def check_provider_health(provider: Any) -> Dict[str, Any]:
    """Execute non-billable health check and compute formal state."""
    pid = getattr(provider, "provider_id", "unknown").lower().strip()
    cb = get_circuit_breaker().get_circuit(pid)
    rl = get_rate_limiter().get_limiter(pid)

    is_enabled = getattr(provider, "enabled", True)
    is_configured = getattr(provider, "is_configured", False)

    # 1. Passive state calculation
    circuit_dict = cb.to_dict()
    rl_dict = rl.to_dict()

    state = compute_health_state(
        provider_id=pid,
        is_enabled=is_enabled,
        is_configured=is_configured,
        circuit_state=circuit_dict["state"],
        in_cooldown=rl_dict["in_cooldown"],
        last_error=circuit_dict.get("last_failure_reason"),
        consecutive_failures=circuit_dict.get("consecutive_failures", 0),
    )

    # 2. If available and configured, run active check_health()
    active_check: Dict[str, Any] = {}
    if state in (HEALTH_AVAILABLE, HEALTH_DEGRADED):
        try:
            if hasattr(provider, "check_health"):
                active_check = await provider.check_health()
            elif hasattr(provider, "health_check"):
                active_check = await provider.health_check()

            if not active_check.get("healthy", True):
                state = HEALTH_DEGRADED
        except Exception as exc:
            state = HEALTH_DEGRADED
            active_check = {"healthy": False, "error": str(exc)}

    return {
        "provider_id": pid,
        "health_state": state,
        "is_enabled": is_enabled,
        "is_configured": is_configured,
        "is_local": getattr(provider, "allow_loopback", False),
        "circuit_breaker": circuit_dict,
        "rate_limiter": rl_dict,
        "active_probe": active_check,
    }


async def inspect_all_provider_health(providers: Dict[str, Any]) -> Dict[str, Any]:
    """Inspect all registered providers concurrently."""
    tasks = [check_provider_health(p) for p in providers.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    summary: Dict[str, Any] = {}
    healthy_count = 0

    for idx, (pid, p) in enumerate(providers.items()):
        res = results[idx]
        if isinstance(res, Exception):
            summary[pid] = {
                "provider_id": pid,
                "health_state": HEALTH_DEGRADED,
                "error": str(res),
            }
        else:
            summary[pid] = res
            if res.get("health_state") == HEALTH_AVAILABLE:
                healthy_count += 1

    return {
        "total_providers": len(providers),
        "available_count": healthy_count,
        "degraded_or_blocked_count": len(providers) - healthy_count,
        "providers": summary,
    }
