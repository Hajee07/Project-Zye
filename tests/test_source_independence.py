"""
Acceptance Test Suite: News Source Independence & Syndication Detection (Day 38 / Phase 3).
Tests 06-12 covering independent publishers, subdomains, duplicates, wire attributions, and ownership groups.
"""

import unittest
from zye_realtime_tactical.news.news_models import IndependenceClassification, NewsArticle
from zye_realtime_tactical.news.publisher_registry import PublisherRegistry
from zye_realtime_tactical.news.syndication_detector import SyndicationDetector


class TestSourceIndependence(unittest.TestCase):
    """Verifies ownership registry matching, wire attribution parsing, and syndication detection."""

    def setUp(self) -> None:
        self.registry = PublisherRegistry.get_instance()
        self.detector = SyndicationDetector(registry=self.registry)

    def test_06_two_distinct_independent_publishers(self):
        """Test 06: BBC and Reuters represent genuinely independent reporting entities."""
        art1 = NewsArticle(
            url="https://www.bbc.com/news/world-123",
            title="Global Climate Summit Agrees on Landmark Emissions Treaty",
            source="BBC News",
            canonical_domain="bbc.com",
            publisher_group="BBC_GROUP",
        )
        art2 = NewsArticle(
            url="https://www.reuters.com/sustainability/climate-summit-treaty",
            title="Delegates Ratify Landmark Climate Accord in Final Session",
            source="Reuters",
            canonical_domain="reuters.com",
            publisher_group="THOMSON_REUTERS",
        )

        res = self.detector.analyze_source_set_independence([art1, art2])
        self.assertEqual(res.independent_publisher_count, 2)
        self.assertFalse(res.duplicates_detected)
        self.assertFalse(res.syndication_detected)
        self.assertEqual(art1.independence, IndependenceClassification.INDEPENDENT)
        self.assertEqual(art2.independence, IndependenceClassification.INDEPENDENT)

    def test_07_same_publisher_different_subdomains(self):
        """Test 07: Subdomains of the same publisher (edition.cnn.com and cnn.com) are classified as SAME_PUBLISHER."""
        art1 = NewsArticle(
            url="https://www.cnn.com/2026/11/20/tech/article-1",
            title="Tech Giant Unveils Quantum Computing Platform",
            canonical_domain="cnn.com",
            publisher_group="WARNER_BROS_DISCOVERY",
        )
        art2 = NewsArticle(
            url="https://edition.cnn.com/2026/11/20/tech/article-1",
            title="Tech Giant Unveils Quantum Computing Platform",
            canonical_domain="cnn.com",
            publisher_group="WARNER_BROS_DISCOVERY",
        )

        rel = self.detector.classify_source_pair(art1, art2)
        self.assertEqual(rel, IndependenceClassification.SAME_PUBLISHER)

    def test_08_duplicate_urls_detected(self):
        """Test 08: Identical or canonical-matching URLs are classified as DUPLICATE."""
        art1 = NewsArticle(
            url="https://www.thehindu.com/news/national/article.html?utm_source=twitter",
            title="Parliament Passes Key Infrastructure Bill",
            canonical_domain="thehindu.com",
            publisher_group="THE_HINDU_GROUP",
        )
        art2 = NewsArticle(
            url="https://www.thehindu.com/news/national/article.html?fbclid=xyz9876",
            title="Parliament Passes Key Infrastructure Bill",
            canonical_domain="thehindu.com",
            publisher_group="THE_HINDU_GROUP",
        )

        rel = self.detector.classify_source_pair(art1, art2)
        self.assertEqual(rel, IndependenceClassification.DUPLICATE)

    def test_09_identical_headline_fingerprint_classified_syndicated(self):
        """Test 09: Distinct regional portals republishing identical text are classified as SYNDICATED."""
        art1 = NewsArticle(
            url="https://www.tribuneindia.com/news/nation/railways-expand-network",
            title="Railway Ministry Announces 500 New Semi-High Speed Trains",
            snippet="The Ministry of Railways today announced a massive rolling stock expansion program.",
            canonical_domain="tribuneindia.com",
            publisher_group="TRIBUNE",
        )
        art2 = NewsArticle(
            url="https://www.deccanherald.com/national/railway-ministry-expansion",
            title="Railway Ministry Announces 500 New Semi-High Speed Trains",
            snippet="The Ministry of Railways today announced a massive rolling stock expansion program.",
            canonical_domain="deccanherald.com",
            publisher_group="DECCAN_HERALD",
        )

        rel = self.detector.classify_source_pair(art1, art2)
        self.assertEqual(rel, IndependenceClassification.SYNDICATED)

    def test_10_shared_wire_attribution_detected(self):
        """Test 10: Explicit attribution to Reuters or AP flags non-independent wire syndication."""
        tag1 = self.detector.detect_wire_attribution("Global Oil Prices Plunge 4% (Reuters)")
        tag2 = self.detector.detect_wire_attribution("Central Bank Holds Rates Steady via Associated Press")
        tag3 = self.detector.detect_wire_attribution("Tech Sector Earnings Surge Reported by Bloomberg")

        self.assertEqual(tag1, "Reuters")
        self.assertEqual(tag2, "Associated Press")
        self.assertEqual(tag3, "Bloomberg News")

    def test_11_corporate_conglomerate_ownership_recognized(self):
        """Test 11: Outlets under Warner Bros Discovery (CNN and Bleacher Report) recognized as affiliated."""
        grp1 = self.registry.resolve_publisher_group("cnn.com")
        grp2 = self.registry.resolve_publisher_group("bleacherreport.com")

        self.assertEqual(grp1, "WARNER_BROS_DISCOVERY")
        self.assertEqual(grp2, "WARNER_BROS_DISCOVERY")
        self.assertTrue(self.registry.are_publishers_affiliated(grp1, grp2))
        self.assertFalse(self.registry.are_independent_publishers("cnn.com", "bleacherreport.com"))

    def test_12_wire_agency_detection_utility(self):
        """Test 12: Wire agencies correctly identified vs general publishers."""
        self.assertTrue(self.registry.is_wire_agency("reuters.com"))
        self.assertTrue(self.registry.is_wire_agency("apnews.com"))
        self.assertTrue(self.registry.is_wire_agency("ptinews.com"))
        self.assertFalse(self.registry.is_wire_agency("bbc.com"))
        self.assertFalse(self.registry.is_wire_agency("thehindu.com"))


if __name__ == "__main__":
    unittest.main()
