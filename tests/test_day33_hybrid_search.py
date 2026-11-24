"""
Tests for Day 33 Hybrid Search Orchestrator & Search Cache.
"""

from __future__ import annotations

import shutil
import time
import unittest
from pathlib import Path

from zye_computer_intelligence.search.hybrid_search_engine import HybridSearchEngine
from zye_computer_intelligence.search.search_cache import SearchCache
from zye_computer_intelligence.search.local_search_engine import LocalSearchEngine
from zye_computer_intelligence.search.local_index_manager import LocalIndexManager
from zye_computer_intelligence.search.web_search_engine import WebSearchEngine
from zye_computer_intelligence.security.local_search_policy import LocalSearchPolicy


class TestDay33HybridSearch(unittest.TestCase):
    """Verifies hybrid search routing, cache TTL handling, and local vs web comparisons."""

    def setUp(self):
        self.root = Path("d:/Zye/scratch/test_hybrid_search_env").resolve()
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True, exist_ok=True)

        (self.root / "system.txt").write_text("Zye hybrid search engine integration test", encoding="utf-8")

        policy = LocalSearchPolicy(allowed_roots=[self.root])
        index_mgr = LocalIndexManager(db_path=self.root / "test_fts.db", policy=policy)
        local_engine = LocalSearchEngine(policy=policy, index_manager=index_mgr)
        self.cache = SearchCache(default_ttl=2.0)
        web_engine = WebSearchEngine()
        # Mock web search to run offline without network delays
        web_engine.search_web = lambda q, **kw: {
            "status": "SUCCESS",
            "results": [{
                "title": "Mock Web Title",
                "content_snippet": "Online documentation for version 33.0.0",
                "url": "https://docs.python.org/3/",
                "domain": "docs.python.org",
            }]
        }
        async def _mock_search_web_async(q, **kw):
            return {
                "status": "SUCCESS",
                "results": [{
                    "title": "Mock Web Title",
                    "content_snippet": "Online documentation for version 33.0.0",
                    "url": "https://docs.python.org/3/",
                    "domain": "docs.python.org",
                }]
            }
        web_engine.search_web_async = _mock_search_web_async

        self.hybrid_engine = HybridSearchEngine(
            local_engine=local_engine,
            web_engine=web_engine,
            cache=self.cache,
        )

    def tearDown(self):
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)

    # --- Search Cache Tests ---

    def test_01_search_cache_set_get_and_expiration(self):
        """Verifies cache returns stored data before TTL and None after TTL expiry."""
        key = SearchCache.generate_cache_key("test query", "local")
        self.assertIsNone(self.cache.get(key))

        self.cache.set(key, {"results": [1, 2, 3]}, ttl=0.1)
        self.assertIsNotNone(self.cache.get(key))

        time.sleep(0.15)
        self.assertIsNone(self.cache.get(key))

    def test_02_search_cache_clear(self):
        """Verifies cache clear purges all stored items."""
        key1 = SearchCache.generate_cache_key("q1", "local")
        key2 = SearchCache.generate_cache_key("q2", "web")
        self.cache.set(key1, "val1")
        self.cache.set(key2, "val2")
        self.assertEqual(len(self.cache._store), 2)

        self.cache.clear()
        self.assertEqual(len(self.cache._store), 0)

    # --- Hybrid Search Engine Execution Tests ---

    def test_03_execute_hybrid_search_local_mode(self):
        """Verifies execute_hybrid_search with local mode operates offline and retrieves local file."""
        res = self.hybrid_engine.execute_hybrid_search(
            query="hybrid search engine integration",
            search_mode="local",
            max_results=5,
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["search_mode"], "local_only")
        self.assertTrue(res["local_results_count"] >= 1)
        self.assertEqual(res["web_results_count"], 0)
        self.assertTrue(len(res["citations"]) >= 1)
        self.assertIn("voice_tanglish", res)
        self.assertIn("voice_en", res)

    def test_04_compare_local_and_web_sources(self):
        """Verifies compare_local_web_sources execution returns comparison structure."""
        res = self.hybrid_engine.compare_local_web_sources(
            local_query="Zye hybrid",
            web_query="Gemini Live",
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("local_results_count", res)
        self.assertIn("web_results_count", res)
        self.assertIn("markdown", res)


if __name__ == "__main__":
    unittest.main()
