"""Intelligent AI Provider Router with Explainable Decisions (Day 27).

Evaluates candidate AI providers dynamically based on:
- Availability and circuit breaker state
- Task type and required model capabilities
- Latency benchmarks and empirical reliability metrics
- Official pricing metadata and token cost estimates
- Privacy restrictions and user preferences
- Generates fully transparent, explainable decision records
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from ..provider_registry import get_provider_registry
from ..resilience.bulkhead import get_bulkhead_manager
from ..resilience.circuit_breaker import STATE_OPEN, get_circuit_breaker
from ..resilience.rate_limiter import get_rate_limiter
from ..telemetry.cost_estimator import estimate_request_cost
from ..telemetry.provider_health import check_provider_health
from ..telemetry.provider_metrics import get_telemetry_registry
from .routing_policy import (
    MODE_BALANCED,
    MODE_COST_FIRST,
    MODE_LOCAL_ONLY,
    MODE_PRIVACY_RESTRICTED,
    MODE_QUALITY_FIRST,
    MODE_RELIABILITY_FIRST,
    MODE_SPEED_FIRST,
    MODE_USER_SELECTED,
    MODE_WEIGHTS,
    normalize_routing_mode,
)

logger = logging.getLogger("zye.ai_plugins.router")

# Base capability scores for models (0.0 to 1.0)
MODEL_CAPABILITIES: Dict[str, Dict[str, float]] = {
    "gpt-4o": {"quality": 0.95, "speed": 0.75, "code": 0.95, "reasoning": 0.95},
    "gpt-4o-mini": {"quality": 0.80, "speed": 0.92, "code": 0.80, "reasoning": 0.78},
    "claude-3-5-sonnet": {"quality": 0.96, "speed": 0.72, "code": 0.98, "reasoning": 0.96},
    "claude-3-5-sonnet-20241022": {"quality": 0.96, "speed": 0.72, "code": 0.98, "reasoning": 0.96},
    "claude-3-haiku": {"quality": 0.75, "speed": 0.90, "code": 0.75, "reasoning": 0.72},
    "llama3.2": {"quality": 0.75, "speed": 0.85, "code": 0.72, "reasoning": 0.70},
    "deepseek-r1": {"quality": 0.92, "speed": 0.65, "code": 0.93, "reasoning": 0.96},
    "sonar-pro": {"quality": 0.88, "speed": 0.70, "code": 0.82, "reasoning": 0.85},
    "deepseek-chat": {"quality": 0.89, "speed": 0.80, "code": 0.90, "reasoning": 0.88},
    "llama-3.3-70b-versatile": {"quality": 0.88, "speed": 0.95, "code": 0.85, "reasoning": 0.86},
}


class RoutingDecision:
    """Explainable result of an intelligent provider routing evaluation."""

    def __init__(
        self,
        request_id: str,
        routing_mode: str,
        selected_provider: str,
        selected_model: str,
        decision_reasons: List[str],
        rejected_candidates: List[Dict[str, Any]],
        estimated_cost: Optional[Dict[str, Any]] = None,
        estimated_latency_ms: Optional[float] = None,
        fallback_allowed: bool = True,
        routing_status: str = "SELECTED",
    ):
        self.request_id = request_id
        self.routing_mode = routing_mode
        self.selected_provider = selected_provider
        self.selected_model = selected_model
        self.decision_reasons = decision_reasons
        self.rejected_candidates = rejected_candidates
        self.estimated_cost = estimated_cost
        self.estimated_latency_ms = estimated_latency_ms
        self.fallback_allowed = fallback_allowed
        self.routing_status = routing_status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "routing_mode": self.routing_mode,
            "selected_provider": self.selected_provider,
            "selected_model": self.selected_model,
            "decision_reasons": self.decision_reasons,
            "rejected_candidates": self.rejected_candidates,
            "estimated_cost": self.estimated_cost,
            "estimated_latency_ms": self.estimated_latency_ms,
            "fallback_allowed": self.fallback_allowed,
            "routing_status": self.routing_status,
        }


def calculate_routing_score(
    provider_id: str,
    model_name: str,
    mode: str,
    reliability_data: Dict[str, Any],
    cost_data: Dict[str, Any],
) -> float:
    """Compute normalized composite routing score (0.0 to 1.0) under chosen mode."""
    caps = MODEL_CAPABILITIES.get(model_name.lower().strip(), {"quality": 0.70, "speed": 0.70})
    quality_score = caps.get("quality", 0.70)

    # Speed score: Invert p50 latency (0ms -> 1.0, 3000ms -> 0.0)
    p50 = reliability_data.get("p50_latency_ms", 500.0)
    speed_score = max(0.1, min(1.0, 1.0 - (p50 / 3000.0))) if p50 > 0 else caps.get("speed", 0.70)

    # Cost score: Free = 1.0, $0.01 = 0.5, >$0.05 = 0.1
    est_cost = cost_data.get("estimated_cost_usd", 0.005) or 0.005
    if provider_id == "ollama" or est_cost == 0.0:
        cost_score = 1.0
    else:
        cost_score = max(0.1, min(1.0, 1.0 - (est_cost * 50.0)))

    # Reliability score
    reliability_score = reliability_data.get("reliability_score", 0.80)

    weights = MODE_WEIGHTS.get(mode, MODE_WEIGHTS[MODE_BALANCED])
    composite = (
        (quality_score * weights["quality"])
        + (speed_score * weights["speed"])
        + (cost_score * weights["cost"])
        + (reliability_score * weights["reliability"])
    )
    return round(composite, 4)


def select_best_provider(
    task: str = "",
    routing_mode: str = "BALANCED",
    user_preferred_provider: Optional[str] = None,
    privacy_restricted: bool = False,
    allow_fallback: bool = True,
    estimated_tokens: int = 250,
) -> RoutingDecision:
    """Evaluate all configured providers and generate an explainable routing decision."""
    req_id = f"route_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    mode = normalize_routing_mode(routing_mode)

    reg = get_provider_registry()
    cb_registry = get_circuit_breaker()
    rl_registry = get_rate_limiter()
    telemetry = get_telemetry_registry()

    # Special Mode 1: USER_SELECTED
    if user_preferred_provider or mode == MODE_USER_SELECTED:
        target_pid = (user_preferred_provider or "").lower().strip()
        provider = reg.get_provider(target_pid)
        if provider:
            # Check Circuit Breaker
            cb_state = cb_registry.get_circuit_state(target_pid)
            if cb_state != STATE_OPEN:
                model = getattr(provider.config, "default_model", target_pid)
                cost_est = estimate_request_cost(target_pid, model, estimated_tokens, estimated_tokens)
                return RoutingDecision(
                    request_id=req_id,
                    routing_mode=MODE_USER_SELECTED,
                    selected_provider=target_pid,
                    selected_model=model,
                    decision_reasons=[
                        f"User explicitly requested provider '{target_pid}'",
                        "Provider is registered and circuit is not OPEN",
                    ],
                    rejected_candidates=[],
                    estimated_cost=cost_est,
                    fallback_allowed=allow_fallback,
                    routing_status="SELECTED_USER_PINNED",
                )
            elif not allow_fallback:
                return RoutingDecision(
                    request_id=req_id,
                    routing_mode=MODE_USER_SELECTED,
                    selected_provider=target_pid,
                    selected_model=getattr(provider.config, "default_model", target_pid),
                    decision_reasons=[f"Provider '{target_pid}' circuit is OPEN and fallback is disabled."],
                    rejected_candidates=[],
                    routing_status="UNAVAILABLE_NO_FALLBACK",
                )

    # Special Mode 2: LOCAL_ONLY or Privacy Restricted
    if mode == MODE_LOCAL_ONLY or privacy_restricted:
        ollama_p = reg.get_provider("ollama")
        if ollama_p:
            model = getattr(ollama_p.config, "default_model", "llama3.2")
            return RoutingDecision(
                request_id=req_id,
                routing_mode=MODE_LOCAL_ONLY,
                selected_provider="ollama",
                selected_model=model,
                decision_reasons=[
                    "Local-Only privacy policy enforced (Air-Gapped Zero Cloud Egress)",
                    "Routed to local Ollama instance on http://127.0.0.1:11434",
                ],
                rejected_candidates=[{"provider": p, "reason": "Cloud API blocked by privacy guard"} for p in reg._providers if p != "ollama"],
                estimated_cost={"cost_status": "CALCULATED", "estimated_cost_usd": 0.0, "is_free_local": True},
                fallback_allowed=False,
                routing_status="SELECTED_AIR_GAPPED",
            )

    # General Mode Evaluation: Score all active candidates
    candidates: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    active_pids = set(reg.get_active_providers())
    # Canonical unique providers
    unique_providers = {}
    for pid in active_pids:
        p = reg.get_provider(pid)
        if p and p.provider_id not in unique_providers:
            unique_providers[p.provider_id] = p

    for pid, provider in unique_providers.items():
        # Check Circuit Breaker
        cb_state = cb_registry.get_circuit_state(pid)
        if cb_state == STATE_OPEN:
            rejected.append({"provider": pid, "reason": "Circuit Breaker is OPEN"})
            continue

        # Check Rate Limiter
        can_proceed, wait_sec, rl_reason = rl_registry.check_capacity(pid, estimated_tokens)
        if not can_proceed and wait_sec > 5.0:
            rejected.append({"provider": pid, "reason": f"Rate limited: {rl_reason}"})
            continue

        model = getattr(provider.config, "default_model", pid)
        cost_info = estimate_request_cost(pid, model, estimated_tokens, estimated_tokens)
        rel_info = telemetry.get_record(pid).calculate_reliability()

        score = calculate_routing_score(pid, model, mode, rel_info, cost_info)
        candidates.append({
            "provider_id": pid,
            "model": model,
            "score": score,
            "cost_info": cost_info,
            "rel_info": rel_info,
        })

    if not candidates:
        # Fallback to local Ollama
        return RoutingDecision(
            request_id=req_id,
            routing_mode=mode,
            selected_provider="ollama",
            selected_model="llama3.2",
            decision_reasons=["All external cloud providers currently degraded or circuit open; fell back to local Ollama."],
            rejected_candidates=rejected,
            routing_status="FALLBACK_EMERGENCY_LOCAL",
        )

    # Sort descending by score
    candidates.sort(key=lambda x: x["score"], reverse=True)
    winner = candidates[0]

    reasons = [
        f"Selected under '{mode}' routing policy with top composite score {winner['score']:.4f}",
        f"Circuit state is healthy and rate limits clear",
        f"Reliability confidence: {winner['rel_info'].get('confidence_label', 'HIGH')}",
    ]
    if mode == MODE_COST_FIRST:
        reasons.append(f"Optimized for cost (Estimated: ${winner['cost_info'].get('estimated_cost_usd', 0.0):.6f})")
    elif mode == MODE_SPEED_FIRST:
        reasons.append(f"Optimized for latency (P50: {winner['rel_info'].get('p50_latency_ms', 0)}ms)")

    # Record alternatives in rejected
    for c in candidates[1:]:
        rejected.append({
            "provider": c["provider_id"],
            "model": c["model"],
            "score": c["score"],
            "reason": f"Lower composite score than {winner['provider_id']} ({c['score']:.4f} vs {winner['score']:.4f})",
        })

    return RoutingDecision(
        request_id=req_id,
        routing_mode=mode,
        selected_provider=winner["provider_id"],
        selected_model=winner["model"],
        decision_reasons=reasons,
        rejected_candidates=rejected,
        estimated_cost=winner["cost_info"],
        estimated_latency_ms=winner["rel_info"].get("p50_latency_ms"),
        fallback_allowed=allow_fallback,
        routing_status="SELECTED",
    )


def select_fallback_provider(
    original_provider: str,
    privacy_restricted: bool = False,
) -> Optional[str]:
    """Select the best eligible alternative when an original provider fails."""
    orig = original_provider.lower().strip()
    if privacy_restricted:
        return "ollama" if orig != "ollama" else None

    # Priority fallback chain
    fallback_map = {
        "chatgpt": ["claude", "deepseek", "groq", "ollama"],
        "openai": ["claude", "deepseek", "groq", "ollama"],
        "claude": ["chatgpt", "deepseek", "groq", "ollama"],
        "anthropic": ["chatgpt", "deepseek", "groq", "ollama"],
        "deepseek": ["groq", "chatgpt", "claude", "ollama"],
        "groq": ["deepseek", "chatgpt", "claude", "ollama"],
        "perplexity": ["chatgpt", "claude", "ollama"],
        "ollama": ["groq", "deepseek", "chatgpt"],  # only if non-private
    }

    chain = fallback_map.get(orig, ["chatgpt", "claude", "ollama"])
    reg = get_provider_registry()
    cb_reg = get_circuit_breaker()

    for candidate in chain:
        p = reg.get_provider(candidate)
        if p and p.is_configured:
            if cb_reg.get_circuit_state(candidate) != STATE_OPEN:
                return candidate

    return "ollama"
