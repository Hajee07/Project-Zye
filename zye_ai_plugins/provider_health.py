"""Non-Billable Health Inspector for Zye AI Multi-AI Plugin Hub.

Executes low-overhead diagnostic checks across providers:
- Model availability checks
- Latency probing
- Authentication validation
- Zero token consumption for health pings
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zye.ai_plugins.health")


async def inspect_provider_health(provider: Any) -> Dict[str, Any]:
    """Run non-billable diagnostic health check on a single provider."""
    try:
        health_result = await provider.check_health()
        return health_result
    except Exception as exc:
        logger.exception("Health check failed for provider %s: %s", getattr(provider, "provider_id", "unknown"), exc)
        return {
            "provider_id": getattr(provider, "provider_id", "unknown"),
            "status": "error",
            "healthy": False,
            "error": str(exc),
            "message": f"Health check threw exception: {type(exc).__name__}",
        }


async def inspect_all_providers(providers: Dict[str, Any]) -> Dict[str, Any]:
    """Concurrently check health across all registered providers."""
    if not providers:
        return {"total": 0, "healthy_count": 0, "results": {}}

    tasks = [inspect_provider_health(p) for p in providers.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    summary_results: Dict[str, Any] = {}
    healthy_count = 0

    for idx, (pid, p) in enumerate(providers.items()):
        res = results[idx]
        if isinstance(res, Exception):
            summary_results[pid] = {
                "provider_id": pid,
                "status": "exception",
                "healthy": False,
                "error": str(res),
            }
        else:
            summary_results[pid] = res
            if res.get("healthy"):
                healthy_count += 1

    return {
        "total_providers": len(providers),
        "healthy_count": healthy_count,
        "unhealthy_count": len(providers) - healthy_count,
        "results": summary_results,
    }
