"""
Acceptance Test Suite: News Retrieval Adapter & Provider Abstraction (Day 38 / Phase 3).
Tests 01-05 covering valid results, empty results, provider failure, invalid metadata, and blank queries.
"""

import unittest
from zye_realtime_tactical.news.news_retriever import NewsRetriever


class TestNewsRetrievalAdapter(unittest.TestCase):
    """Verifies non-blocking news retrieval, mock provider injection, and error handling."""

    def tearDown(self) -> None:
        NewsRetriever.reset_mock_provider()

    def test_01_valid_results_mock_provider(self):
        """Test 01: Valid results returned from injected mock provider."""
        def _mock(topic: str, max_results: int):
            return [
                {
                    "url": "https://www.reuters.com/world/india/space-mission",
                    "title": "Space Agency Launches Earth Observation Satellite",
                    "body": "The satellite was successfully placed into orbit.",
                    "source": "Reuters",
                    "date": "2026-11-20T12:00:00Z",
                }
            ]

        NewsRetriever.set_mock_provider(_mock)
        status, items, err = NewsRetriever.fetch_news_results_sync("space mission", max_results=5)
        self.assertEqual(status, "SUCCESS")
        self.assertEqual(len(items), 1)
        self.assertIsNone(err)
        self.assertEqual(items[0]["source"], "Reuters")

    def test_02_no_results_returned(self):
        """Test 02: Zero results handled cleanly without exceptions."""
        def _mock_empty(topic: str, max_results: int):
            return []

        NewsRetriever.set_mock_provider(_mock_empty)
        status, items, err = NewsRetriever.fetch_news_results_sync("completely non-existent topic xyz123")
        self.assertEqual(status, "NO_RESULTS")
        self.assertEqual(len(items), 0)
        self.assertIn("0 articles", err)

    def test_03_provider_failure_handling(self):
        """Test 03: External provider exceptions return NEWS_PROVIDER_UNAVAILABLE without crash."""
        def _mock_fail(topic: str, max_results: int):
            raise ConnectionError("DNS resolution failed or rate limit exceeded")

        NewsRetriever.set_mock_provider(_mock_fail)
        status, items, err = NewsRetriever.fetch_news_results_sync("breaking news")
        self.assertEqual(status, "NEWS_PROVIDER_UNAVAILABLE")
        self.assertEqual(len(items), 0)
        self.assertIn("Mock provider error", err)

    def test_04_empty_or_whitespace_topic_rejected(self):
        """Test 04: Blank or whitespace query is rejected immediately without search invocation."""
        called = [False]
        def _mock(topic: str, max_results: int):
            called[0] = True
            return []

        NewsRetriever.set_mock_provider(_mock)
        status, items, err = NewsRetriever.fetch_news_results_sync("   \n\t  ")
        self.assertEqual(status, "NO_RESULTS")
        self.assertEqual(len(items), 0)
        self.assertFalse(called[0])

    def test_05_max_results_parameter_respected(self):
        """Test 05: Mock provider receives exact max_results requested."""
        passed_max = [0]
        def _mock(topic: str, max_results: int):
            passed_max[0] = max_results
            return [{"url": f"https://example.com/{i}", "title": f"T{i}"} for i in range(max_results)]

        NewsRetriever.set_mock_provider(_mock)
        status, items, err = NewsRetriever.fetch_news_results_sync("quantum computing", max_results=4)
        self.assertEqual(status, "SUCCESS")
        self.assertEqual(passed_max[0], 4)
        self.assertEqual(len(items), 4)


if __name__ == "__main__":
    unittest.main()
