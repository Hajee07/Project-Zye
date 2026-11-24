"""
Tests for Day 33 Result Normalization, Multi-Factor Ranking, Evidence Validation, and Citations.
"""

from __future__ import annotations

import unittest
from zye_computer_intelligence.search.search_result_normalizer import SearchResultNormalizer
from zye_computer_intelligence.search.search_result_ranker import SearchResultRanker
from zye_computer_intelligence.search.evidence_validation_engine import EvidenceValidationEngine
from zye_computer_intelligence.search.citation_builder import CitationBuilder


class TestDay33RankingCitations(unittest.TestCase):
    """Verifies search result normalization, multi-factor ranking, evidence validation, and citations."""

    def test_01_result_normalization_and_deduplication(self):
        """Verifies local and web results are normalized and deduplicated."""
        local_raw = [
            {"file_path": "d:/Zye/main.py", "file_name": "main.py", "content_snippet": "assistant"},
            {"file_path": "d:/Zye/main.py", "file_name": "main.py", "content_snippet": "duplicate"},
        ]
        web_raw = [
            {"url": "https://docs.python.org/3/", "title": "Python 3 Docs", "snippet": "Official docs"},
            {"url": "https://docs.python.org/3/?utm_source=test", "title": "Python 3 Docs", "snippet": "Dup"},
        ]

        normalized = SearchResultNormalizer.normalize_results(
            local_results=local_raw,
            web_results=web_raw,
        )

        self.assertEqual(len(normalized), 2)  # 1 local + 1 web after deduplication
        self.assertEqual(normalized[0]["source_type"], "local")
        self.assertEqual(normalized[1]["source_type"], "web")
        self.assertEqual(normalized[1]["domain"], "docs.python.org")

    def test_02_ranker_exact_phrase_and_domain_authority(self):
        """Verifies ranking score boosts for exact phrase matches and official domains."""
        query = "Python asyncio event loop"

        official_res = {
            "title": "Python asyncio event loop documentation",
            "content_snippet": "Detailed guide on asyncio event loop in python",
            "source_type": "web",
            "domain": "docs.python.org",
        }
        random_res = {
            "title": "My personal blog note",
            "content_snippet": "Mentioning python and loops",
            "source_type": "web",
            "domain": "randomblog.org",
        }

        score_official = SearchResultRanker.calculate_relevance_score(official_res, query)
        score_random = SearchResultRanker.calculate_relevance_score(random_res, query)

        self.assertGreater(score_official, score_random)
        self.assertGreater(score_official, 0.70)

    def test_03_rank_and_sort_result_list(self):
        """Verifies results list is sorted descending by relevance score."""
        query = "FastAPI endpoints"
        results = [
            {"title": "Unrelated topic", "content_snippet": "nothing here", "source_type": "web"},
            {"title": "FastAPI endpoints guide", "content_snippet": "building endpoints", "source_type": "web", "domain": "github.com"},
        ]
        ranked = SearchResultRanker.rank_results(results, query)
        self.assertEqual(ranked[0]["title"], "FastAPI endpoints guide")
        self.assertGreater(ranked[0]["relevance_score"], ranked[1]["relevance_score"])

    def test_04_evidence_validation_consensus_and_conflicts(self):
        """Verifies evidence validation identifies multiple corroborated sources and version conflicts."""
        results = [
            {
                "citation_id": "c1",
                "source_type": "local",
                "title": "Version Config",
                "content_snippet": "Project version 33.0.0 is deployed",
            },
            {
                "citation_id": "c2",
                "source_type": "web",
                "title": "Release Notes",
                "content_snippet": "Latest release is version 33.0.0 on PyPI",
            },
        ]
        evidence = EvidenceValidationEngine.validate_evidence(results, target_claim="version 33.0.0")
        self.assertEqual(evidence["status"], "SUCCESS")
        self.assertEqual(evidence["corroboration_status"], "PARTIALLY_CORROBORATED")
        self.assertEqual(evidence["confidence_level"], "MEDIUM")
        self.assertEqual(evidence["total_sources_count"], 2)

    def test_05_citation_builder_markdown_and_voice(self):
        """Verifies Markdown footnotes and bilingual voice summary generation."""
        results = [
            {
                "citation_id": "local_1",
                "source_type": "local",
                "title": "main.py",
                "file_path": "d:/Zye/main.py",
                "file_name": "main.py",
            },
            {
                "citation_id": "web_2",
                "source_type": "web",
                "title": "Python Docs",
                "url": "https://docs.python.org/3/",
                "domain": "docs.python.org",
            },
        ]
        citations = CitationBuilder.build_citations(results)
        self.assertEqual(len(citations), 2)
        self.assertEqual(citations[0]["citation_marker"], "[1]")
        self.assertEqual(citations[1]["citation_marker"], "[2]")

        # Markdown footnotes
        md_text = CitationBuilder.format_markdown_citations(citations)
        self.assertIn("main.py", md_text)
        self.assertIn("Python Docs", md_text)

        # Voice summaries
        tanglish, english = CitationBuilder.format_voice_citations(citations)
        self.assertIn("Found 2 sources", english)
        self.assertIn("sources irukku", tanglish)


if __name__ == "__main__":
    unittest.main()
