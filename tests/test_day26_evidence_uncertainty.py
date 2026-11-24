"""Day 26 Unit Tests: Evidence Verification and Uncertainty Analysis.

Tests:
- Detection of hedge phrases, qualifiers, and speculation
- Qualitative uncertainty tiering (HIGH, MODERATE, LOW, INSUFFICIENT)
- Evidence coverage ratio and identification of unsupported assumptions
"""

import unittest

from zye_ai_plugins.claim_extractor import NormalizedClaim
from zye_ai_plugins.evidence_analyzer import (
    analyze_answer_uncertainty,
    evaluate_evidence_coverage,
    identify_unsupported_assumptions,
)


class TestDay26EvidenceUncertainty(unittest.TestCase):
    """Test suite for Evidence and Uncertainty Analyzer."""

    def test_01_high_uncertainty_detection(self):
        """Verify answers with multiple hedge words evaluate to LOW EVIDENCE SUPPORT."""
        speculative_text = (
            "It might possibly be true that this approach works, but perhaps it seems "
            "untested in my opinion. Presumably latency could be acceptable as far as I know."
        )
        claims = [
            NormalizedClaim(provider_id="p1", claim_text="It might possibly be true", claim_type="assumption"),
            NormalizedClaim(provider_id="p1", claim_text="Presumably latency is low", claim_type="assumption"),
        ]

        unc = analyze_answer_uncertainty(speculative_text, claims)
        self.assertEqual(unc["evidence_tier"], "LOW EVIDENCE SUPPORT")
        self.assertTrue(unc["is_unverified"])
        self.assertGreaterEqual(unc["hedge_phrases_count"], 4)

    def test_02_high_evidence_grounding(self):
        """Verify concrete assertions with numerical claims evaluate to HIGH EVIDENCE SUPPORT."""
        empirical_text = (
            "We measured 12ms latency across 5000 QPS. The cache hit ratio is 98.4%. "
            "PostgreSQL handles 1200 writes per second without connection drop."
        )
        claims = [
            NormalizedClaim(provider_id="p1", claim_text="Measured 12ms latency across 5000 QPS", claim_type="numerical"),
            NormalizedClaim(provider_id="p1", claim_text="Cache hit ratio is 98.4%", claim_type="numerical"),
            NormalizedClaim(provider_id="p1", claim_text="PostgreSQL handles 1200 writes per second", claim_type="factual"),
        ]

        unc = analyze_answer_uncertainty(empirical_text, claims)
        self.assertEqual(unc["evidence_tier"], "HIGH EVIDENCE SUPPORT")
        self.assertFalse(unc["is_unverified"])
        self.assertEqual(unc["hedge_phrases_count"], 0)

    def test_03_unsupported_assumptions_isolated(self):
        """Verify unsupported assumptions are extracted cleanly."""
        claims = [
            NormalizedClaim(provider_id="p1", claim_text="Assuming that the network has zero packet loss", claim_type="assumption"),
            NormalizedClaim(provider_id="p1", claim_text="Given that all clients support HTTP/3", claim_type="technical"),
            NormalizedClaim(provider_id="p1", claim_text="Python handles 100k threads natively", claim_type="factual"),
        ]

        assumptions = identify_unsupported_assumptions(claims)
        self.assertGreaterEqual(len(assumptions), 2)
        self.assertIn("Assuming that the network has zero packet loss", assumptions)


if __name__ == "__main__":
    unittest.main()
