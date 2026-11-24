"""Day 26 Unit Tests: Disagreement Detection and Severity Ranking.

Tests:
- Categorized disagreement detection (TECHNICAL, SECURITY, PERFORMANCE)
- Severity ranking: CRITICAL > HIGH > MEDIUM > LOW
- Structured disagreement report generation
"""

import unittest

from zye_ai_plugins.claim_extractor import NormalizedClaim
from zye_ai_plugins.disagreement_detector import (
    classify_disagreement,
    detect_disagreements,
    generate_disagreement_report,
    rank_disagreement_severity,
)


class TestDay26Disagreement(unittest.TestCase):
    """Test suite for Disagreement Detection Engine."""

    def test_01_security_contradiction_critical(self):
        """Verify conflicting security claims are classified as CRITICAL severity."""
        ca = NormalizedClaim(provider_id="chatgpt", claim_text="The authentication layer is completely secure", topic="security")
        cb = NormalizedClaim(provider_id="claude", claim_text="The authentication layer is not secure against injection", topic="security")

        dag = classify_disagreement(ca, cb)
        self.assertIsNotNone(dag)
        self.assertEqual(dag.category, "SECURITY")
        self.assertEqual(dag.severity, "CRITICAL")
        self.assertEqual(dag.resolution_status, "UNRESOLVED")

    def test_02_competing_recommendations(self):
        """Verify competing recommendations on architecture are detected as HIGH severity."""
        ca = NormalizedClaim(provider_id="chatgpt", claim_text="I recommend using FastAPI microservices", claim_type="recommendation", topic="architecture")
        cb = NormalizedClaim(provider_id="claude", claim_text="I recommend using a monolithic Django architecture", claim_type="recommendation", topic="architecture")

        dag = classify_disagreement(ca, cb)
        self.assertIsNotNone(dag)
        self.assertEqual(dag.category, "TECHNICAL")
        self.assertEqual(dag.severity, "HIGH")

    def test_03_detect_disagreements_batch(self):
        """Verify detect_disagreements detects all pairwise conflicts across providers."""
        c_gpt = [
            NormalizedClaim(provider_id="chatgpt", claim_text="Architecture A is completely secure", topic="security"),
            NormalizedClaim(provider_id="chatgpt", claim_text="Latency will be 5ms", claim_type="numerical", topic="performance"),
        ]
        c_cld = [
            NormalizedClaim(provider_id="claude", claim_text="Architecture A is not secure and dangerous", topic="security"),
            NormalizedClaim(provider_id="claude", claim_text="Latency will be 50ms", claim_type="numerical", topic="performance"),
        ]

        dags = detect_disagreements({"chatgpt": c_gpt, "claude": c_cld})
        self.assertGreaterEqual(len(dags), 2)
        # Verify CRITICAL severity sorts first
        self.assertEqual(dags[0].severity, "CRITICAL")

    def test_04_generate_disagreement_report(self):
        """Verify disagreement report structure and critical flags."""
        ca = NormalizedClaim(provider_id="chatgpt", claim_text="System is safe", topic="security")
        cb = NormalizedClaim(provider_id="claude", claim_text="System is not safe", topic="security")
        dags = detect_disagreements({"chatgpt": [ca], "claude": [cb]})

        report = generate_disagreement_report(dags)
        self.assertEqual(report["total_disagreements"], 1)
        self.assertEqual(report["critical_count"], 1)
        self.assertTrue(report["requires_evidence_resolution"])


if __name__ == "__main__":
    unittest.main()
