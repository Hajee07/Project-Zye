"""
Tests for Day 33 Search Query Planner & Multi-Lingual Intent Classifier.
"""

from __future__ import annotations

import unittest
from zye_computer_intelligence.search.search_query_planner import (
    SearchQueryPlanner,
    SearchMode,
    SearchIntent,
)


class TestDay33QueryPlanner(unittest.TestCase):
    """Verifies intent classification across English, Tamil, and Tanglish queries."""

    def test_01_classify_local_search_intents_english(self):
        """Verifies local file, code, and document search queries are classified as LOCAL_ONLY."""
        local_queries = [
            "search my local documents for tax invoice",
            "find python files in my local project",
            "look up resume.pdf in my laptop files",
            "search local datasets for customer records",
            "find error logs in my local workspace",
        ]
        for query in local_queries:
            plan = SearchQueryPlanner.plan_query(query)
            self.assertEqual(
                plan.mode,
                SearchMode.LOCAL_ONLY,
                f"Failed for query '{query}': got {plan.mode}",
            )

    def test_02_classify_web_search_intents_english(self):
        """Verifies web, internet, online, and browsing queries are classified as WEB_ONLY."""
        web_queries = [
            "search web for python 3.12 documentation",
            "google latest generative ai announcements",
            "browse internet for current weather in chennai",
            "look up online tutorials for fastapi",
            "find web news about gemini live",
        ]
        for query in web_queries:
            plan = SearchQueryPlanner.plan_query(query)
            self.assertEqual(
                plan.mode,
                SearchMode.WEB_ONLY,
                f"Failed for query '{query}': got {plan.mode}",
            )

    def test_03_classify_hybrid_search_intents(self):
        """Verifies comparison, cross-referencing, and verification queries are classified as HYBRID."""
        hybrid_queries = [
            "compare my local budget with latest tax rates online",
            "cross-reference my local notes with web sources",
            "verify this local specification against online standards",
            "hybrid search for project architecture both local and web",
        ]
        for query in hybrid_queries:
            plan = SearchQueryPlanner.plan_query(query)
            self.assertEqual(
                plan.mode,
                SearchMode.HYBRID,
                f"Failed for query '{query}': got {plan.mode}",
            )

    def test_04_classify_tanglish_queries(self):
        """Verifies Tanglish queries classify correctly for local and web."""
        tanglish_local = [
            "laptop la resume enga irukku paaru",
            "en documents la report file thedu",
            "local files la python code search pannu",
        ]
        for query in tanglish_local:
            plan = SearchQueryPlanner.plan_query(query)
            self.assertEqual(
                plan.mode,
                SearchMode.LOCAL_ONLY,
                f"Tanglish local failed for '{query}': got {plan.mode}",
            )

        tanglish_web = [
            "net la python tutorial thedu",
            "online la latest news paaru",
            "web search pannu chennai weather pathi",
        ]
        for query in tanglish_web:
            plan = SearchQueryPlanner.plan_query(query)
            self.assertEqual(
                plan.mode,
                SearchMode.WEB_ONLY,
                f"Tanglish web failed for '{query}': got {plan.mode}",
            )

    def test_05_classify_tamil_unicode_queries(self):
        """Verifies Tamil script queries classify properly."""
        tamil_local = "என் உள்ளூர் கோப்புகளில் அறிக்கையை தேடு"
        plan_local = SearchQueryPlanner.plan_query(tamil_local)
        self.assertEqual(plan_local.mode, SearchMode.LOCAL_ONLY)

        tamil_web = "இணையத்தில் புதிய செய்திகளை தேடு"
        plan_web = SearchQueryPlanner.plan_query(tamil_web)
        self.assertEqual(plan_web.mode, SearchMode.WEB_ONLY)

    def test_06_filter_extraction_and_entities(self):
        """Verifies file type filters, domain filters, and entity extraction."""
        plan = SearchQueryPlanner.plan_query("search python code and pdf documents site:python.org")
        self.assertIn(".py", plan.file_type_filters)
        self.assertIn(".pdf", plan.file_type_filters)
        self.assertIn("python.org", plan.domain_filters)

    def test_07_query_expansion_variants(self):
        """Verifies query planner generates search query expansion variants."""
        intent = SearchQueryPlanner.plan_query("python asyncio site:docs.python.org")
        expanded = SearchQueryPlanner.expand_query(intent)
        self.assertTrue(len(expanded) >= 1)
        self.assertTrue(any("docs.python.org" in q for q in expanded))


if __name__ == "__main__":
    unittest.main()
