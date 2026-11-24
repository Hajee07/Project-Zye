"""
ZYE AI — Hybrid Model Router & Failover Engine
==============================================

Implements Section 08 & Section 09 of Master Engineering Specification.
Manages dynamic model routing across:
1. Gemini Master Brain Primary Models (gemini-2.5-pro, gemini-2.5-flash, gemini-3.8-live)
2. Model Circuit Breaker failover chaining
3. Local model execution when hardware permits and task is suitable
4. Strict fallback to Gemini Cloud whenever local inference is degraded
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from zye_core.event_bus import ZyeEventBus
from zye_core.types import ModelCircuitState, ZyeEvent, ZyeEventType
from zye_intelligence.circuit_breaker import ModelCircuitBreaker
from zye_intelligence.local_readiness import LocalReadinessDetector
from zye_intelligence.model_registry import ModelCapability, ModelHealthRegistry
from zye_reliability.resource_governor import ResourceGovernor

logger = logging.getLogger("zye.intelligence.hybrid_router")


@dataclass(slots=True)
class RoutingVerdict:
    """Decision produced by HybridModelRouter."""

    selected_model: str
    is_local: bool
    fallback_chain: List[str]
    rationale: str


class HybridModelRouter:
    """
    Intelligently routes inference requests based on query requirements,
    circuit breaker health, and system resource headroom.
    Gemini Master Brain is ALWAYS the primary brain.
    """

    PRIMARY_PRO_MODEL = "gemini-2.5-pro"
    PRIMARY_FLASH_MODEL = "gemini-2.5-flash"
    DEFAULT_FALLBACK_CHAIN = ["gemini-2.5-pro", "gemini-2.5-flash"]

    def __init__(
        self,
        circuit_breaker: Optional[ModelCircuitBreaker] = None,
        health_registry: Optional[ModelHealthRegistry] = None,
        governor: Optional[ResourceGovernor] = None,
        readiness_detector: Optional[LocalReadinessDetector] = None,
        event_bus: Optional[ZyeEventBus] = None,
    ) -> None:
        self.circuit_breaker = circuit_breaker or ModelCircuitBreaker()
        self.health_registry = health_registry or ModelHealthRegistry()
        self.governor = governor or ResourceGovernor()
        self.readiness_detector = readiness_detector or LocalReadinessDetector(governor=self.governor)
        self.event_bus = event_bus

    def route_request(
        self,
        query: str,
        requires_deep_reasoning: bool = False,
        prefer_offline: bool = False,
    ) -> RoutingVerdict:
        """
        Determines the optimal model to handle the incoming request.
        """
        # 1. If prefer_offline requested, test local model readiness and resource gate
        if prefer_offline:
            profile = self.readiness_detector.evaluate_readiness()
            if profile.is_ready_for_local_inference:
                return RoutingVerdict(
                    selected_model="local-model-default",
                    is_local=True,
                    fallback_chain=[self.PRIMARY_FLASH_MODEL],
                    rationale="Prefer offline requested and local runtime headroom verified.",
                )
            else:
                logger.info("Local inference requested but unavailable (%s). Using Gemini.", profile.status_reason)

        # 2. Select initial target model based on reasoning complexity
        target = self.PRIMARY_PRO_MODEL if requires_deep_reasoning else self.PRIMARY_FLASH_MODEL

        # 3. Check circuit breaker status on chosen target
        if self.circuit_breaker.allow_request(target):
            return RoutingVerdict(
                selected_model=target,
                is_local=False,
                fallback_chain=[m for m in self.DEFAULT_FALLBACK_CHAIN if m != target],
                rationale=f"Selected {target} based on query complexity. Circuit closed.",
            )

        # 4. Target circuit is OPEN -> Failover to fallback
        fallback = self.PRIMARY_FLASH_MODEL if target == self.PRIMARY_PRO_MODEL else self.PRIMARY_PRO_MODEL
        if self.circuit_breaker.allow_request(fallback):
            logger.warning(
                "Primary model '%s' circuit is OPEN! Failing over to fallback '%s'.",
                target,
                fallback,
            )
            return RoutingVerdict(
                selected_model=fallback,
                is_local=False,
                fallback_chain=[],
                rationale=f"Primary model {target} circuit tripped. Failing over to {fallback}.",
            )

        # 5. Both Gemini models tripped -> Check if local inference can act as emergency fallback
        profile = self.readiness_detector.evaluate_readiness()
        if profile.is_ready_for_local_inference:
            logger.critical("All Gemini circuits OPEN! Deploying emergency local inference.")
            return RoutingVerdict(
                selected_model="local-model-default",
                is_local=True,
                fallback_chain=[],
                rationale="All cloud Gemini gateways tripped. Emergency local model activated.",
            )

        # Fail closed
        return RoutingVerdict(
            selected_model=target,
            is_local=False,
            fallback_chain=[],
            rationale="All models currently degraded or unavailable.",
        )


__all__ = [
    "RoutingVerdict",
    "HybridModelRouter",
]
