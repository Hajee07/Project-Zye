"""
Acceptance Test Suite: Claim-Level Cross-Source Corroboration Engine (Day 38 / Phase 3).
Tests 19-24 covering proposition extraction, multi-source corroboration, numerical & date contradictions,
corrections detection, and single-source unverified statuses.
"""

import unittest
from zye_realtime_tactical.news.claim_corroborator import ClaimCorroborator
from zye_realtime_tactical.news.news_models import IndependenceClassification, NewsArticle


class TestClaimCorroborationEngine(unittest.TestCase):
    """Verifies atomic proposition matching, evidence matrix construction, and contradiction handling."""

    def test_19_corroboration_of_identical_factual_claim(self):
        """Test 19: Corroboration of same core proposition across 2 independent sources yields CORROBORATED."""
        art1 = NewsArticle(
            url="https://www.reuters.com/tech/quantum-breakthrough",
            title="Tech Lab Demonstrates 1,000-Qubit Quantum Processor with Error Correction",
            snippet="Researchers announced a 1,000-qubit quantum processor achieving low error rates.",
            source="Reuters",
            canonical_domain="reuters.com",
            publisher_group="THOMSON_REUTERS",
            independence=IndependenceClassification.INDEPENDENT,
            timestamp_status="VALID_UTC",
            published_at_utc="2026-11-20T10:00:00Z",
        )
        art2 = NewsArticle(
            url="https://www.nature.com/articles/quantum-processor-milestone",
            title="Milestone 1,000-Qubit Quantum Processor Achieves Fault-Tolerant Operations",
            snippet="A novel architecture demonstrated 1,000-qubit stability in continuous runtime tests.",
            source="Nature",
            canonical_domain="nature.com",
            publisher_group="SPRINGER_NATURE",
            independence=IndependenceClassification.INDEPENDENT,
            timestamp_status="VALID_UTC",
            published_at_utc="2026-11-20T10:30:00Z",
        )

        claim = ClaimCorroborator.evaluate_claim_corroboration(
            claim_text="1,000-qubit quantum processor demonstration",
            articles=[art1, art2],
        )

        self.assertEqual(claim.status, "CORROBORATED")
        self.assertEqual(claim.supporting_source_count, 2)
        self.assertEqual(len(claim.contradicting_sources), 0)

    def test_20_distinct_claim_rejection(self):
        """Test 20: Completely unrelated incident articles do not match the requested proposition."""
        art = NewsArticle(
            url="https://www.bbc.com/sport/football-match-result",
            title="City Secures Dramatic 3-2 Victory in Championship Final",
            snippet="The team clinched the title in extra time.",
            source="BBC Sport",
            canonical_domain="bbc.com",
            publisher_group="BBC_GROUP",
            independence=IndependenceClassification.INDEPENDENT,
            timestamp_status="VALID_UTC",
        )

        supports, score, _ = ClaimCorroborator.do_articles_support_same_claim(
            claim_text="Central Bank lowers benchmark interest rate by 50 basis points",
            article=art,
        )
        self.assertFalse(supports)
        self.assertLess(score, 0.30)

    def test_21_numerical_contradiction_detected(self):
        """Test 21: Conflicting numbers (e.g. $15B vs $12B) on the same corporate report flag a contradiction."""
        art1 = NewsArticle(
            url="https://reuters.com/a1",
            title="Global Auto Corp posts Q3 operating profit of $15.2 billion",
            snippet="Automaker reported record third-quarter operating profit of $15.2 billion.",
            source="Reuters",
            canonical_domain="reuters.com",
            publisher_group="THOMSON_REUTERS",
            independence=IndependenceClassification.INDEPENDENT,
            published_timestamp=1763640000.0,
        )
        art2 = NewsArticle(
            url="https://bloomberg.com/a2",
            title="Global Auto Corp posts Q3 operating profit of $12.1 billion",
            snippet="Automaker reported third-quarter operating profit of $12.1 billion, missing estimates.",
            source="Bloomberg",
            canonical_domain="bloomberg.com",
            publisher_group="BLOOMBERG",
            independence=IndependenceClassification.INDEPENDENT,
            published_timestamp=1763640300.0,
        )

        contradictions = ClaimCorroborator.detect_contradictions([art1, art2])
        self.assertEqual(len(contradictions), 1)
        self.assertEqual(contradictions[0].conflict_type, "NUMERICAL")
        self.assertEqual(contradictions[0].field, "number")
        self.assertIn("15.2", contradictions[0].source_a_value)
        self.assertIn("12.1", contradictions[0].source_b_value)

    def test_22_temporal_date_contradiction_detected(self):
        """Test 22: Conflicting dates (e.g. November 20 vs December 15) flag a contradiction."""
        art1 = NewsArticle(
            url="https://source1.com/a1",
            title="Space Agency Schedules Mars Probe Launch for November 20",
            snippet="Official timeline sets probe launch on November 20 from spaceport.",
            source="Source 1",
            canonical_domain="source1.com",
            publisher_group="GROUP_1",
            published_timestamp=1763640000.0,
        )
        art2 = NewsArticle(
            url="https://source2.com/a2",
            title="Space Agency Schedules Mars Probe Launch for December 15",
            snippet="Agency rescheduled the Mars probe mission to December 15 due to sensor checks.",
            source="Source 2",
            canonical_domain="source2.com",
            publisher_group="GROUP_2",
            published_timestamp=1763641000.0,
        )

        contradictions = ClaimCorroborator.detect_contradictions([art1, art2])
        self.assertTrue(any(c.conflict_type in ("DATE", "NUMERICAL") for c in contradictions))

    def test_23_explicit_correction_detected(self):
        """Test 23: Newer article containing 'revised' or 'correction' flags is_correction=True."""
        art1 = NewsArticle(
            url="https://reuters.com/a1",
            title="Port authority reports 25 vessels delayed in shipping channel",
            snippet="Initial reports indicate 25 vessels delayed.",
            source="Reuters",
            canonical_domain="reuters.com",
            publisher_group="THOMSON_REUTERS",
            published_timestamp=1763640000.0,
        )
        art2 = NewsArticle(
            url="https://reuters.com/a2",
            title="CORRECTION: Port authority reports revised 14 vessels delayed in shipping channel",
            snippet="The port authority issued a revised tally stating 14 vessels were affected.",
            source="Reuters",
            canonical_domain="reuters.com",
            publisher_group="THOMSON_REUTERS",
            published_timestamp=1763643600.0,  # 1 hour later
        )

        contradictions = ClaimCorroborator.detect_contradictions([art1, art2])
        self.assertTrue(len(contradictions) > 0)
        self.assertTrue(contradictions[0].is_correction)
        self.assertEqual(contradictions[0].newer_source_url, "https://reuters.com/a2")

    def test_24_single_source_unverified_evaluation(self):
        """Test 24: Single supporting source results in SINGLE_SOURCE_UNVERIFIED status."""
        art = NewsArticle(
            url="https://reuters.com/single-scoop",
            title="Diplomatic Delegation Concludes Confidential Talks in Geneva",
            snippet="Envoys wrapped up three days of confidential bilateral negotiations.",
            source="Reuters",
            canonical_domain="reuters.com",
            publisher_group="THOMSON_REUTERS",
            independence=IndependenceClassification.INDEPENDENT,
            timestamp_status="VALID_UTC",
            published_at_utc="2026-11-20T10:00:00Z",
        )

        claim = ClaimCorroborator.evaluate_claim_corroboration(
            claim_text="Confidential Geneva diplomatic delegation talks",
            articles=[art],
        )
        self.assertEqual(claim.status, "SINGLE_SOURCE_UNVERIFIED")
        self.assertEqual(claim.supporting_source_count, 1)


if __name__ == "__main__":
    unittest.main()
