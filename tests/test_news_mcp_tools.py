"""
Acceptance Test Suite: FastMCP News Tools Registration & Verification Status (Day 38 / Phase 3).
Tests 31-35 covering total tool registration (19 tools), schema validation, source independence tool,
operational status tool, and voice proactive alert gating.
"""

from datetime import datetime, timezone
import unittest
from zye_realtime_tactical.news.news_models import VerificationStatus
from zye_realtime_tactical.news.news_retriever import NewsRetriever
from zye_realtime_tactical.news.verification_engine import NewsVerificationEngine
import realtime_tactical_mcp


class TestNewsMCPTools(unittest.TestCase):
    """Verifies FastMCP tool registration, schemas, and operational health."""

    def tearDown(self) -> None:
        NewsRetriever.reset_mock_provider()

    def test_31_fastmcp_registered_tool_count_is_19(self):
        """Test 31: FastMCP server exports exactly 19 registered tools."""
        registered_tools = getattr(realtime_tactical_mcp.mcp, "_tools", {})
        if hasattr(realtime_tactical_mcp.mcp, "_tool_manager"):
            registered_tools = realtime_tactical_mcp.mcp._tool_manager._tools

        self.assertEqual(len(registered_tools), 19)
        self.assertIn("fetch_verified_live_updates", registered_tools)
        self.assertIn("verify_specific_news_claim", registered_tools)
        self.assertIn("analyze_news_source_independence", registered_tools)
        self.assertIn("get_news_verification_status", registered_tools)

    def test_32_analyze_news_source_independence_tool(self):
        """Test 32: analyze_news_source_independence tool executes synchronously and returns structured evaluation."""
        sample_articles = [
            {
                "url": "https://www.reuters.com/tech/quantum",
                "title": "Quantum Computing Architecture Milestone Announced by Research Lab",
                "snippet": "Researchers demonstrated a working fault-tolerant multi-qubit machine.",
                "source": "Reuters",
                "canonical_domain": "reuters.com",
                "publisher_group": "THOMSON_REUTERS",
            },
            {
                "url": "https://www.bbc.com/news/science-quantum",
                "title": "Scientists Reveal Landmark Breakthrough in Quantum Processing Systems",
                "snippet": "A novel processor topology successfully reduced operational decoherence errors.",
                "source": "BBC",
                "canonical_domain": "bbc.com",
                "publisher_group": "BBC_GROUP",
            },
        ]
        res = realtime_tactical_mcp.analyze_news_source_independence(articles=sample_articles)
        self.assertEqual(res.get("total_sources_evaluated"), 2)
        self.assertEqual(res.get("independent_publisher_count"), 2)
        self.assertFalse(res.get("duplicates_detected"))

    def test_33_get_news_verification_status_tool(self):
        """Test 33: get_news_verification_status tool returns runtime telemetry."""
        res = realtime_tactical_mcp.get_news_verification_status()
        self.assertEqual(res.get("status"), "SUCCESS")
        engine_status = res.get("news_engine", {})
        self.assertEqual(engine_status.get("engine_status"), "OPERATIONAL")
        self.assertIn("verification_policy", engine_status)
        self.assertEqual(engine_status["verification_policy"]["minimum_independent_sources"], 2)

    def test_34_sync_verification_engine_topic_validation(self):
        """Test 34: NewsVerificationEngine executes deterministic verification with mock provider."""
        def _mock_provider(topic: str, max_results: int):
            return [
                {
                    "url": "https://www.reuters.com/world/asia/spacecraft-landing",
                    "title": "Lunar Lander Successfully Touches Down on Moon Surface",
                    "body": "The unmanned lander completed a precision touchdown near the lunar south pole.",
                    "source": "Reuters",
                    "date": "2026-11-20T12:00:00Z",
                },
                {
                    "url": "https://www.bbc.com/news/science-space-lunar",
                    "title": "Space Agency Confirms Successful Touchdown of Lunar Lander",
                    "body": "Telemetry confirms the robotic explorer made contact with the lunar regolith safely.",
                    "source": "BBC",
                    "date": "2026-11-20T12:20:00Z",
                },
            ]

        NewsRetriever.set_mock_provider(_mock_provider)
        engine = NewsVerificationEngine()
        as_of = datetime(2026, 11, 20, 18, 0, 0, tzinfo=timezone.utc).timestamp()
        res = engine.verify_topic_sync(
            topic="Lunar lander moon touchdown",
            freshness_window_hours=72.0,
            as_of_timestamp=as_of,
        )

        self.assertEqual(res.status, VerificationStatus.CORROBORATED)
        self.assertTrue(res.proactive_alert_eligible)
        self.assertEqual(res.source_summary["independent_sources"], 2)
        self.assertIn("Zye Verified Update", res.voice_summary)

    def test_35_unverified_voice_summary_fallback(self):
        """Test 35: When fewer than 2 independent sources exist, Tamil/Tanglish voice fallback is emitted."""
        def _mock_single(topic: str, max_results: int):
            return [
                {
                    "url": "https://www.reuters.com/tech/single-story",
                    "title": "Exclusive Report on Autonomous Drone Fleet",
                    "body": "Single agency report on prototype fleet.",
                    "source": "Reuters",
                    "date": "2026-11-20T12:00:00Z",
                }
            ]

        NewsRetriever.set_mock_provider(_mock_single)
        engine = NewsVerificationEngine()
        as_of = datetime(2026, 11, 20, 18, 0, 0, tzinfo=timezone.utc).timestamp()
        res = engine.verify_topic_sync(
            topic="Autonomous drone fleet prototype",
            freshness_window_hours=72.0,
            as_of_timestamp=as_of,
        )

        self.assertEqual(res.status, VerificationStatus.SINGLE_SOURCE_UNVERIFIED)
        self.assertFalse(res.proactive_alert_eligible)
        self.assertIn("single source mattumae report pannirukku", res.voice_summary)


if __name__ == "__main__":
    unittest.main()
