"""Cost Estimator and Pricing Rate Card for Zye AI Multi-AI Hub (Day 27).

Provides mathematical cost estimation and tracking across external models:
- Configurable official model pricing rate card (per 1M input / output tokens)
- Distinguishes free local compute (Ollama = $0.00) from commercial APIs
- Reports "UNKNOWN" when pricing metadata is missing (never fabricates pricing)
- Cost comparison and budget analysis
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("zye.ai_plugins.cost")

# Pricing rate card per 1,000,000 tokens (USD)
# (input_price_per_1m, output_price_per_1m)
DEFAULT_MODEL_PRICING: Dict[str, Tuple[float, float]] = {
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "o1": (15.00, 60.00),
    "o3-mini": (1.10, 4.40),
    # Anthropic
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-haiku": (0.25, 1.25),
    "claude-3-5-haiku-20241022": (0.80, 4.00),
    # Local Ollama (Free local execution)
    "llama3.2": (0.00, 0.00),
    "llama3.1": (0.00, 0.00),
    "deepseek-r1": (0.00, 0.00),
    "qwen2.5-coder": (0.00, 0.00),
    "mistral": (0.00, 0.00),
    # Perplexity
    "sonar-pro": (3.00, 15.00),
    "sonar": (1.00, 1.00),
    # DeepSeek Cloud
    "deepseek-chat": (0.14, 0.28),
    "deepseek-reasoner": (0.55, 2.19),
    # Groq Cloud
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
    # OpenRouter Generic Fallback
    "openrouter-default": (1.00, 3.00),
}


def lookup_model_pricing(model_name: str, provider_id: str = "") -> Optional[Tuple[float, float]]:
    """Lookup (input_price_per_1m, output_price_per_1m) for a model."""
    m_lower = (model_name or "").lower().strip()
    p_lower = (provider_id or "").lower().strip()

    if p_lower == "ollama":
        return (0.00, 0.00)

    # Direct match
    if m_lower in DEFAULT_MODEL_PRICING:
        return DEFAULT_MODEL_PRICING[m_lower]

    # Partial match
    for k, v in DEFAULT_MODEL_PRICING.items():
        if k in m_lower or m_lower in k:
            return v

    return None


def estimate_request_cost(
    provider_id: str,
    model: str,
    estimated_input_tokens: int = 500,
    estimated_output_tokens: int = 300,
) -> Dict[str, Any]:
    """Estimate the cost of a future request."""
    pricing = lookup_model_pricing(model, provider_id)
    if pricing is None:
        return {
            "provider_id": provider_id,
            "model": model,
            "is_estimated": True,
            "pricing_available": False,
            "cost_status": "UNKNOWN",
            "estimated_cost_usd": None,
            "message": f"Pricing rate card not configured for model '{model}'",
        }

    in_price_1m, out_price_1m = pricing
    cost = (estimated_input_tokens / 1_000_000.0 * in_price_1m) + (estimated_output_tokens / 1_000_000.0 * out_price_1m)

    return {
        "provider_id": provider_id,
        "model": model,
        "is_estimated": True,
        "pricing_available": True,
        "cost_status": "CALCULATED",
        "estimated_input_tokens": estimated_input_tokens,
        "estimated_output_tokens": estimated_output_tokens,
        "estimated_cost_usd": round(cost, 6),
        "input_price_per_1m": in_price_1m,
        "output_price_per_1m": out_price_1m,
        "currency": "USD",
    }


def calculate_actual_cost(
    provider_id: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> Dict[str, Any]:
    """Calculate actual billable cost from verified token counts."""
    pricing = lookup_model_pricing(model, provider_id)
    if pricing is None:
        return {
            "provider_id": provider_id,
            "model": model,
            "cost_status": "UNKNOWN",
            "actual_cost_usd": None,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

    in_price_1m, out_price_1m = pricing
    cost = (prompt_tokens / 1_000_000.0 * in_price_1m) + (completion_tokens / 1_000_000.0 * out_price_1m)

    return {
        "provider_id": provider_id,
        "model": model,
        "cost_status": "VERIFIED",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "actual_cost_usd": round(cost, 6),
        "currency": "USD",
    }


def compare_provider_costs(
    input_tokens: int = 1000,
    output_tokens: int = 500,
) -> List[Dict[str, Any]]:
    """Compare estimated costs across all configured models."""
    comparisons = []
    for model_name, (in_p, out_p) in DEFAULT_MODEL_PRICING.items():
        cost = (input_tokens / 1_000_000.0 * in_p) + (output_tokens / 1_000_000.0 * out_p)
        comparisons.append({
            "model": model_name,
            "cost_usd": round(cost, 6),
            "input_price_per_1m": in_p,
            "output_price_per_1m": out_p,
            "is_free_local": (in_p == 0.0 and out_p == 0.0),
        })

    return sorted(comparisons, key=lambda x: x["cost_usd"])
