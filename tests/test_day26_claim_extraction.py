"""Day 26 Unit Tests: Claim Extraction and Normalization Engine.

Tests:
- Extraction of atomic claims from free-form AI text
- Categorization into technical, recommendation, numerical, assumption, security
- Normalization and deduplication
- Semantic overlap and contradiction detection between claim pairs
"""

import unittest

from zye_ai_plugins.claim_extractor import (
    NormalizedClaim,
    classify_claims,
    compare_claims,
    extract_response_claims,
    normalize_claims,
)


class TestDay26ClaimExtraction(unittest.TestCase):
    """Test suite for claim extraction and normalization."""

    def test_01_extract_claims_variety(self):
        """Verify extraction and categorization of varied claim types."""
        text = (
            "I recommend adopting FastAPI for the new microservices architecture.\n"
            "Architecture A provides lower latency of 15ms per request under peak load.\n"
            "Assuming that PostgreSQL can handle the concurrent write throughput.\n"
            "Insecure eval or exec functions create critical code execution vulnerabilities.\n"
            "Python 3.12 contains native sub-interpreters and improved performance.\n"
        )

        claims = extract_response_claims("chatgpt", text)
        self.assertGreaterEqual(len(claims), 4)

        types_found = {c.claim_type for c in claims}
        self.assertIn("recommendation", types_found)
        self.assertIn("numerical", types_found)
        self.assertIn("assumption", types_found)
        self.assertIn("security", types_found)

    def test_02_normalize_and_deduplicate(self):
        """Verify duplicate claims across formatting differences are merged."""
        c1 = NormalizedClaim(provider_id="chatgpt", claim_text="FastAPI has high performance.")
        c2 = NormalizedClaim(provider_id="claude", claim_text="FastAPI has high performance!")
        c3 = NormalizedClaim(provider_id="ollama", claim_text="Django is a full-featured framework.")

        normalized = normalize_claims([c1, c2, c3])
        self.assertEqual(len(normalized), 2)
        texts = [c.claim_text for c in normalized]
        self.assertIn("Django is a full-featured framework.", texts)

    def test_03_classify_claims(self):
        """Verify claims group correctly into dictionary buckets."""
        c_rec = NormalizedClaim(provider_id="p1", claim_text="Use Redis for caching", claim_type="recommendation")
        c_sec = NormalizedClaim(provider_id="p2", claim_text="Validate SSL tokens", claim_type="security")
        c_num = NormalizedClaim(provider_id="p3", claim_text="Memory is 256MB", claim_type="numerical")

        grouped = classify_claims([c_rec, c_sec, c_num])
        self.assertEqual(len(grouped["recommendation"]), 1)
        self.assertEqual(len(grouped["security"]), 1)
        self.assertEqual(len(grouped["numerical"]), 1)

    def test_04_compare_claims_contradiction(self):
        """Verify contradiction detection on opposing claims sharing a topic."""
        ca = NormalizedClaim(
            provider_id="chatgpt",
            claim_text="Architecture A is completely secure against remote threats",
            claim_type="technical",
            topic="security",
        )
        cb = NormalizedClaim(
            provider_id="claude",
            claim_text="Architecture A is not secure against remote threats and has vulnerabilities",
            claim_type="technical",
            topic="security",
        )

        cmp_res = compare_claims(ca, cb)
        self.assertTrue(cmp_res["is_same_topic"])
        self.assertTrue(cmp_res["is_contradiction"])
        self.assertGreaterEqual(cmp_res["overlap_score"], 0.25)


if __name__ == "__main__":
    unittest.main()
