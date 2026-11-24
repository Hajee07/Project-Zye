"""
Tests for Day 33 Computer Intelligence MCP Server Tools Registration & Invocations.
"""

from __future__ import annotations

import unittest
from computer_intelligence_mcp import (
    mcp,
    search_local_sources,
    search_local_code,
    search_local_documents,
    search_local_datasets,
    get_local_index_status,
    extract_web_content,
    verify_search_evidence,
    get_search_citations,
    refresh_search_results,
    rebuild_local_search_index,
)


class TestDay33SearchMCP(unittest.TestCase):
    """Verifies that all 45 FastMCP tools are registered and search tools execute correctly."""

    def test_01_verify_total_mcp_tool_count(self):
        """Verifies exactly 45 unique tools are registered on the FastMCP server."""
        tools_dict = getattr(mcp, "_tool_manager", None)
        if tools_dict and hasattr(tools_dict, "_tools"):
            registered_tools = list(tools_dict._tools.keys())
        else:
            registered_tools = [f.__name__ for f in getattr(mcp, "_tools", [])]

        self.assertEqual(
            len(registered_tools),
            45,
            f"Expected 45 tools, found {len(registered_tools)}: {registered_tools}",
        )

    def test_02_verify_search_tools_presence(self):
        """Verifies all 17 Day 33 search intelligence tools exist in registration."""
        tools_dict = getattr(mcp, "_tool_manager", None)
        registered_tools = set(tools_dict._tools.keys())

        expected_search_tools = {
            "search_local_sources",
            "search_local_documents",
            "search_local_code",
            "search_local_datasets",
            "search_web_sources",
            "search_web_domain",
            "fetch_web_page",
            "extract_web_content",
            "execute_hybrid_search",
            "compare_local_web_sources",
            "verify_search_evidence",
            "get_search_citations",
            "get_local_index_status",
            "rebuild_local_search_index",
            "get_search_job_status",
            "cancel_search_job",
            "refresh_search_results",
        }
        missing = expected_search_tools - registered_tools
        self.assertEqual(len(missing), 0, f"Missing search tools: {missing}")

    def test_03_invoke_search_local_sources(self):
        """Verifies search_local_sources returns valid JSON with search results."""
        res = search_local_sources(query="main.py", max_results=3)
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertIn("results", res)
        self.assertTrue(isinstance(res["results"], list))

    def test_04_invoke_search_local_code(self):
        """Verifies search_local_code locates code definitions."""
        res = search_local_code(query="def ", max_results=3)
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertTrue(res.get("results_count", 0) >= 1 or len(res.get("results", [])) >= 1)

    def test_05_invoke_get_local_index_status(self):
        """Verifies get_local_index_status returns FTS5 database stats."""
        res = get_local_index_status()
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertIn("indexed_documents_count", res)

    def test_06_invoke_extract_web_content(self):
        """Verifies extract_web_content parses HTML content."""
        sample_html = "<html><head><title>Test Article</title></head><body><p>Article content here.</p></body></html>"
        res = extract_web_content(html_content=sample_html, source_url="https://example.com/test")
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertEqual(res["title"], "Test Article")
        self.assertIn("Article content here", res["content"])

    def test_07_invoke_verify_search_evidence(self):
        """Verifies verify_search_evidence returns structured evidence assessment."""
        res = verify_search_evidence(query="local Zye assistant version")
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertIn("confidence_level", res)
        self.assertIn("corroboration_status", res)

    def test_08_invoke_get_search_citations(self):
        """Verifies get_search_citations returns markdown and voice formatting."""
        res = get_search_citations(query="local Zye assistant", search_mode="local")
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertIn("citations", res)
        self.assertIn("markdown", res)
        self.assertIn("voice_tanglish", res)
        self.assertIn("voice_en", res)

    def test_09_invoke_cache_and_rebuild(self):
        """Verifies refresh_search_results and rebuild_local_search_index."""
        cache_res = refresh_search_results(query="main.py", search_mode="local")
        self.assertEqual(cache_res.get("status"), "SUCCESS")

        idx_res = rebuild_local_search_index(root_dir="d:/Zye/scratch")
        self.assertEqual(idx_res.get("status"), "SUCCESS")


if __name__ == "__main__":
    unittest.main()
