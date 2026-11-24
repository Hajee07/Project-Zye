"""Day 27 Unit Tests: Intelligent AI Provider Router & Policies.

Tests:
- Routing mode scoring across BALANCED, QUALITY_FIRST, SPEED_FIRST, COST_FIRST, RELIABILITY_FIRST
- Strict LOCAL_ONLY mode enforcement (100% offline air-gapped)
- Strict USER_SELECTED provider pinning and fallback permission checks
- Explainable RoutingDecision record schema
- Fallback provider chain resolution
"""

import unittest
from unittest.mock import MagicMock, patch

from zye_ai_plugins.routing import (
    MODE_BALANCED,
    MODE_COST_FIRST,
    MODE_LOCAL_ONLY,
    MODE_QUALITY_FIRST,
    MODE_RELIABILITY_FIRST,
    MODE_SPEED_FIRST,
    MODE_USER_SELECTED,
    calculate_routing_score,
    normalize_routing_mode,
    select_best_provider,
    select_fallback_provider,
)


class TestDay27ProviderRouter(unittest.TestCase):
    """Test suite for intelligent provider router and policies."""

    def test_01_mode_normalization(self):
        """Verify string inputs normalize cleanly to valid routing modes."""
        self.assertEqual(normalize_routing_mode("fast"), MODE_SPEED_FIRST)
        self.assertEqual(normalize_routing_mode("cheap"), MODE_COST_FIRST)
        self.assertEqual(normalize_routing_mode("local"), MODE_LOCAL_ONLY)
        self.assertEqual(normalize_routing_mode("best"), MODE_QUALITY_FIRST)
        self.assertEqual(normalize_routing_mode("unknown_mode"), MODE_BALANCED)

    def test_02_calculate_routing_score_differentiates(self):
        """Verify scoring shifts accurately according to selected routing mode."""
        rel_data = {"reliability_score": 0.95, "p50_latency_ms": 120.0}
        cost_cheap = {"estimated_cost_usd": 0.0001}
        cost_expensive = {"estimated_cost_usd": 0.0200}

        # Under COST_FIRST mode, cheap model scores significantly higher
        score_cheap = calculate_routing_score("ollama", "llama3.2", MODE_COST_FIRST, rel_data, cost_cheap)
        score_exp = calculate_routing_score("openai", "gpt-4o", MODE_COST_FIRST, rel_data, cost_expensive)
        self.assertGreater(score_cheap, score_exp)

        # Under QUALITY_FIRST mode, top-tier model scores higher
        score_quality_top = calculate_routing_score("anthropic", "claude-3-5-sonnet", MODE_QUALITY_FIRST, rel_data, cost_expensive)
        score_quality_small = calculate_routing_score("ollama", "llama3.2", MODE_QUALITY_FIRST, rel_data, cost_cheap)
        self.assertGreater(score_quality_top, score_quality_small)

    def test_03_local_only_mode_air_gapped(self):
        """Verify LOCAL_ONLY mode strictly selects Ollama and rejects all cloud APIs."""
        dec = select_best_provider(task="internal code audit", routing_mode="LOCAL_ONLY")
        self.assertEqual(dec.selected_provider, "ollama")
        self.assertEqual(dec.routing_mode, MODE_LOCAL_ONLY)
        self.assertIn("Local-Only", dec.decision_reasons[0])
        self.assertFalse(dec.fallback_allowed)
        self.assertEqual(dec.routing_status, "SELECTED_AIR_GAPPED")

    def test_04_user_selected_pinning(self):
        """Verify USER_SELECTED honors explicit user choice."""
        dec = select_best_provider(
            task="write documentation",
            routing_mode=MODE_USER_SELECTED,
            user_preferred_provider="claude",
        )
        self.assertEqual(dec.selected_provider, "claude")
        self.assertEqual(dec.routing_status, "SELECTED_USER_PINNED")
        self.assertIn("User explicitly requested", dec.decision_reasons[0])

    def test_05_select_fallback_chain(self):
        """Verify fallback provider resolution respects privacy and availability."""
        # Non-private fallback for chatgpt
        fb_cloud = select_fallback_provider("chatgpt", privacy_restricted=False)
        self.assertIn(fb_cloud, ("claude", "deepseek", "groq", "ollama"))

        # Privacy-restricted fallback must only be local ollama
        fb_private = select_fallback_provider("chatgpt", privacy_restricted=True)
        self.assertEqual(fb_private, "ollama")


if __name__ == "__main__":
    unittest.main()
