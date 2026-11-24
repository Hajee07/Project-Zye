"""Day 26 Unit Tests: Consensus Analysis and Minority Perspective Engine.

Tests:
- Full agreement, partial agreement, and contradictory consensus states
- Isolation of unique minority positions
- Protection against false-consensus majority fallacy
"""

import unittest

from zye_ai_plugins.claim_extractor import NormalizedClaim
from zye_ai_plugins.consensus_analyzer import analyze_consensus
from zye_ai_plugins.disagreement_detector import DisagreementItem


class TestDay26Consensus(unittest.TestCase):
    """Test suite for Consensus Analysis Engine."""

    def test_01_full_agreement(self):
        """Verify 100% shared claims evaluate to FULL_AGREEMENT."""
        c1 = NormalizedClaim(provider_id="chatgpt", claim_text="Async I/O optimizes network throughput", topic="performance")
        c2 = NormalizedClaim(provider_id="claude", claim_text="Async I/O optimizes network throughput", topic="performance")

        res = analyze_consensus({"chatgpt": [c1], "claude": [c2]}, [])
        self.assertEqual(res["consensus_status"], "FULL_AGREEMENT")
        self.assertEqual(res["agreement_score"], 1.0)
        self.assertEqual(res["shared_points_count"], 1)

    def test_02_contradictory_consensus_override(self):
        """Verify presence of critical disagreements overrides consensus to CONTRADICTORY_POSITIONS."""
        c1 = NormalizedClaim(provider_id="chatgpt", claim_text="Async I/O optimizes network throughput", topic="performance")
        c2 = NormalizedClaim(provider_id="claude", claim_text="Async I/O optimizes network throughput", topic="performance")
        critical_dag = DisagreementItem(
            category="SECURITY",
            topic="security",
            provider_a="chatgpt",
            provider_b="claude",
            position_a="Safe",
            position_b="Not safe",
            explanation="Critical conflict",
            severity="CRITICAL",
        )

        res = analyze_consensus({"chatgpt": [c1], "claude": [c2]}, [critical_dag])
        self.assertEqual(res["consensus_status"], "CONTRADICTORY_POSITIONS")
        self.assertEqual(res["critical_disagreements_count"], 1)

    def test_03_minority_position_isolated(self):
        """Verify unique perspectives are preserved as minority positions rather than discarded."""
        c_gpt = [
            NormalizedClaim(provider_id="chatgpt", claim_text="Use Redis for caching", topic="architecture"),
            NormalizedClaim(provider_id="chatgpt", claim_text="Deploy with Docker containers", topic="devops"),
        ]
        c_cld = [
            NormalizedClaim(provider_id="claude", claim_text="Deploy with Docker containers", topic="devops"),
            NormalizedClaim(provider_id="claude", claim_text="Consider memory fragmentation in high-write Redis", topic="performance"),
        ]

        res = analyze_consensus({"chatgpt": c_gpt, "claude": c_cld}, [])
        self.assertEqual(res["consensus_status"], "PARTIAL_AGREEMENT")
        self.assertGreaterEqual(res["minority_positions_count"], 1)
        minority_topics = [m["topic"] for m in res["minority_positions"]]
        self.assertIn("performance", minority_topics)


if __name__ == "__main__":
    unittest.main()
