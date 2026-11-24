"""Day 27 Unit Tests: Cost Estimation, Health State Machine & Telemetry Analytics.

Tests:
- Pricing rate card lookup and cost estimation
- Missing pricing metadata reports UNKNOWN status without fabrication
- Health state taxonomy evaluation
- Rolling percentile latency calculation
- Reliability ranking with sample size confidence penalties
"""

import unittest

from zye_ai_plugins.telemetry import (
    HEALTH_AUTH_FAILED,
    HEALTH_AVAILABLE,
    HEALTH_CIRCUIT_OPEN,
    HEALTH_CONFIGURED,
    HEALTH_DEGRADED,
    HEALTH_DISABLED,
    HEALTH_RATE_LIMITED,
    RollingLatencyTracker,
    TelemetryRegistry,
    calculate_actual_cost,
    compare_provider_costs,
    compute_health_state,
    estimate_request_cost,
    lookup_model_pricing,
)


class TestDay27CostAndTelemetry(unittest.TestCase):
    """Test suite for cost, health, and telemetry analytics."""

    def test_01_pricing_rate_card_and_estimation(self):
        """Verify cost estimation for commercial and free local models."""
        # Commercial model (gpt-4o: $2.50 / $10.00 per 1M)
        est_gpt = estimate_request_cost("chatgpt", "gpt-4o", 1000, 500)
        self.assertEqual(est_gpt["cost_status"], "CALCULATED")
        # (1000/1M * 2.50) + (500/1M * 10.00) = 0.0025 + 0.0050 = 0.0075
        self.assertAlmostEqual(est_gpt["estimated_cost_usd"], 0.0075, places=5)

        # Free local model (ollama: $0.00)
        est_ollama = estimate_request_cost("ollama", "llama3.2", 1000, 500)
        self.assertEqual(est_ollama["cost_status"], "CALCULATED")
        self.assertEqual(est_ollama["estimated_cost_usd"], 0.0)

    def test_02_unknown_pricing_not_fabricated(self):
        """Verify unknown models return UNKNOWN status instead of fabricating cost."""
        est_unknown = estimate_request_cost("custom", "fictional-model-999", 1000, 500)
        self.assertEqual(est_unknown["cost_status"], "UNKNOWN")
        self.assertIsNone(est_unknown["estimated_cost_usd"])
        self.assertFalse(est_unknown["pricing_available"])

    def test_03_health_state_taxonomy(self):
        """Verify formal health state transitions across conditions."""
        # Disabled
        s_dis = compute_health_state("p1", is_enabled=False, is_configured=True, circuit_state="CLOSED", in_cooldown=False)
        self.assertEqual(s_dis, HEALTH_DISABLED)

        # Configured but not yet verified
        s_cfg = compute_health_state("p1", is_enabled=True, is_configured=False, circuit_state="CLOSED", in_cooldown=False)
        self.assertEqual(s_cfg, HEALTH_CONFIGURED)

        # Circuit Open
        s_cb = compute_health_state("p1", is_enabled=True, is_configured=True, circuit_state="OPEN", in_cooldown=False)
        self.assertEqual(s_cb, HEALTH_CIRCUIT_OPEN)

        # Rate Limited
        s_rl = compute_health_state("p1", is_enabled=True, is_configured=True, circuit_state="CLOSED", in_cooldown=True)
        self.assertEqual(s_rl, HEALTH_RATE_LIMITED)

        # Auth Failed
        s_auth = compute_health_state("p1", is_enabled=True, is_configured=True, circuit_state="CLOSED", in_cooldown=False, last_error="Invalid_api_key provided")
        self.assertEqual(s_auth, HEALTH_AUTH_FAILED)

        # Healthy Available
        s_ok = compute_health_state("p1", is_enabled=True, is_configured=True, circuit_state="CLOSED", in_cooldown=False)
        self.assertEqual(s_ok, HEALTH_AVAILABLE)

    def test_04_rolling_percentile_latencies(self):
        """Verify rolling statistical percentiles (P50, P90, P95, P99)."""
        tracker = RollingLatencyTracker(max_samples=100)
        # Record latencies 10ms to 100ms
        for lat in range(10, 110, 10):
            tracker.record(float(lat))

        pcts = tracker.get_percentiles()
        self.assertGreaterEqual(pcts["p50"], 50.0)
        self.assertGreaterEqual(pcts["p95"], 90.0)
        self.assertEqual(pcts["avg"], 55.0)

    def test_05_reliability_ranking_sample_confidence(self):
        """Verify reliability ranking applies sample size confidence damping."""
        tel = TelemetryRegistry()
        rec_few = tel.get_record("prov_few_samples")
        rec_many = tel.get_record("prov_many_samples")

        # 2 successful calls
        rec_few.record_request(success=True, latency_ms=100.0)
        rec_few.record_request(success=True, latency_ms=100.0)

        # 20 successful calls
        for _ in range(20):
            rec_many.record_request(success=True, latency_ms=120.0)

        rel_few = rec_few.calculate_reliability()
        rel_many = rec_many.calculate_reliability()

        self.assertEqual(rel_few["confidence_label"], "LOW_SAMPLE_CONFIDENCE")
        self.assertEqual(rel_many["confidence_label"], "HIGH_SAMPLE_CONFIDENCE")

        # High sample provider with 20 successes ranks ahead of low-sample provider
        ranks = tel.rank_providers_by_reliability()
        many_rank = next(r["rank"] for r in ranks if r["provider_id"] == "prov_many_samples")
        few_rank = next(r["rank"] for r in ranks if r["provider_id"] == "prov_few_samples")
        self.assertLess(many_rank, few_rank)


if __name__ == "__main__":
    unittest.main()
