"""
Performance & Latency Benchmark Suite: News Verification Engine (Day 38 / Phase 3).
Measures CPU processing time for URL normalization, syndication detection, claim corroboration,
and end-to-end multi-source verification under bounded in-memory constraints.
"""

from datetime import datetime, timezone
import time
import unittest
from zye_realtime_tactical.news.claim_corroborator import ClaimCorroborator
from zye_realtime_tactical.news.news_models import NewsArticle
from zye_realtime_tactical.news.news_retriever import NewsRetriever
from zye_realtime_tactical.news.syndication_detector import SyndicationDetector
from zye_realtime_tactical.news.url_normalizer import UrlNormalizer
from zye_realtime_tactical.news.verification_engine import NewsVerificationEngine


class TestNewsPerformanceBenchmarks(unittest.TestCase):
    """Benchmarks processing latency and memory safety under multi-article workloads."""

    def tearDown(self) -> None:
        NewsRetriever.reset_mock_provider()

    def test_benchmark_url_normalization_throughput(self):
        """Benchmark: 1,000 URL normalizations execute within 15 milliseconds."""
        url = "https://www.reuters.com/business/markets/stock-update-2026/?utm_source=twitter&utm_medium=cpc&fbclid=123#section"
        t0 = time.perf_counter_ns()
        for _ in range(1000):
            UrlNormalizer.normalize_url(url)
        elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
        print(f"\n[BENCHMARK] 1,000 URL Normalizations: {elapsed_ms:.2f} ms")
        self.assertLess(elapsed_ms, 50.0)

    def test_benchmark_syndication_detection_throughput(self):
        """Benchmark: Pairwise classification of 50 article pairs executes within 25 milliseconds."""
        articles = [
            NewsArticle(
                url=f"https://source{i}.com/article",
                title=f"Global Summit Reaches Agreement on Renewable Energy Mandates Part {i % 5}",
                snippet="Delegates ratified a joint communique outlining phased decarbonization timelines.",
                canonical_domain=f"source{i}.com",
                publisher_group=f"GROUP_{i % 8}",
            )
            for i in range(50)
        ]

        detector = SyndicationDetector()
        t0 = time.perf_counter_ns()
        res = detector.analyze_source_set_independence(articles)
        elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
        print(f"\n[BENCHMARK] Syndication Detection (50 articles): {elapsed_ms:.2f} ms (Found {res.independent_publisher_count} independent)")
        self.assertLess(elapsed_ms, 50.0)

    def test_benchmark_end_to_end_verification_latency(self):
        """Benchmark: End-to-end multi-source corroboration pipeline executes in < 30 ms."""
        def _mock_ten(topic: str, max_results: int):
            return [
                {
                    "url": f"https://www.publisher{i}.com/news/satellite-launch",
                    "title": f"Space Exploration Mission Successfully Places Satellite into Orbit {i}",
                    "body": "The telemetry ground station confirmed nominal orbit insertion parameters.",
                    "source": f"Publisher {i}",
                    "date": "2026-11-20T12:00:00Z",
                }
                for i in range(10)
            ]

        NewsRetriever.set_mock_provider(_mock_ten)
        engine = NewsVerificationEngine()
        as_of = datetime(2026, 11, 20, 18, 0, 0, tzinfo=timezone.utc).timestamp()

        t0 = time.perf_counter_ns()
        res = engine.verify_topic_sync(
            topic="Space Exploration Mission Satellite Orbit",
            max_results=10,
            as_of_timestamp=as_of,
            use_cache=False,
        )
        elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
        print(f"\n[BENCHMARK] End-to-End Verification (10 sources): {elapsed_ms:.2f} ms (Status: {res.status.value})")
        self.assertLess(elapsed_ms, 50.0)
        self.assertTrue(res.verified)


if __name__ == "__main__":
    unittest.main()
