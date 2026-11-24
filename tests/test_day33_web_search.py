"""
Tests for Day 33 Web Search: DOM Sanitization, HTML Parsing, and Provider Query Abstraction.
"""

from __future__ import annotations

import unittest
from zye_computer_intelligence.search.web_content_extractor import WebContentExtractor
from zye_computer_intelligence.search.web_search_engine import (
    DuckDuckGoHtmlProvider,
    WebSearchEngine,
)


class TestDay33WebSearch(unittest.TestCase):
    """Verifies HTML content parsing, DOM extraction, and web search engine providers."""

    # --- Web Content Extractor Tests ---

    def test_01_extract_html_content_strips_scripts_and_styles(self):
        """Verifies HTML DOM parser strips script/style tags and extracts clean text."""
        raw_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Page Title</title>
            <style>body { color: red; }</style>
            <script>console.log("bad script");</script>
        </head>
        <body>
            <header><nav>Navigation Link</nav></header>
            <article>
                <h1>Main Heading</h1>
                <p>This is the first paragraph with important information about Gemini Live.</p>
                <p>Second paragraph containing architectural details.</p>
            </article>
            <footer>Copyright 2026</footer>
        </body>
        </html>
        """
        parsed = WebContentExtractor.parse_html(raw_html, source_url="https://example.com/test")
        self.assertEqual(parsed.title, "Test Page Title")
        self.assertIn("Main Heading", parsed.text_content)
        self.assertIn("important information about Gemini Live", parsed.text_content)
        self.assertNotIn("bad script", parsed.text_content)
        self.assertNotIn("color: red", parsed.text_content)

    def test_02_extract_metadata_and_paragraphs(self):
        """Verifies paragraph splitting and metadata extraction."""
        html = """
        <html>
        <head>
            <meta name="description" content="A comprehensive tutorial on Python data science.">
            <meta name="author" content="Dr. Smith">
        </head>
        <body>
            <p>First paragraph.</p>
            <p>Second paragraph.</p>
        </body>
        </html>
        """
        parsed = WebContentExtractor.parse_html(html, source_url="https://example.com/meta")
        self.assertEqual(parsed.meta_description, "A comprehensive tutorial on Python data science.")
        self.assertTrue(len(parsed.paragraphs) >= 2)

    def test_03_malformed_html_handling(self):
        """Verifies parser does not crash on broken or malformed HTML."""
        broken_html = "<div><p>Unclosed paragraph<div><span>Random text"
        parsed = WebContentExtractor.parse_html(broken_html, source_url="https://example.com/broken")
        self.assertIn("Random text", parsed.text_content)

    # --- Web Search Engine & Provider Tests ---

    def test_04_provider_url_construction(self):
        """Verifies provider properly encodes query and applies site filtering."""
        provider = DuckDuckGoHtmlProvider()
        url = provider.build_search_url(
            query="python async tutorial",
            site_filter="docs.python.org",
        )
        self.assertIn("duckduckgo.com/html", url)
        self.assertIn("python+async+tutorial", url)
        self.assertIn("site%3Adocs.python.org", url)

    def test_05_provider_html_result_parsing(self):
        """Verifies DuckDuckGo HTML parser extracts title, URL, and snippet."""
        sample_ddg_html = """
        <div class="result results_links results_links_deep web-result">
            <h2 class="result__title">
                <a class="result__url" href="https://docs.python.org/3/library/asyncio.html">asyncio — Asynchronous I/O</a>
            </h2>
            <div class="result__snippet">
                asyncio is a library to write concurrent code using the async/await syntax.
            </div>
        </div>
        """
        provider = DuckDuckGoHtmlProvider()
        results = provider.parse_search_results(sample_ddg_html)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "asyncio — Asynchronous I/O")
        self.assertIn("docs.python.org", results[0].url)
        self.assertIn("concurrent code", results[0].snippet)

    def test_06_web_search_engine_domain_filtering(self):
        """Verifies WebSearchEngine applies domain filtering."""
        engine = WebSearchEngine()
        provider = DuckDuckGoHtmlProvider()
        url = provider.build_search_url("duckdb", site_filter="duckdb.org")
        self.assertIn("site%3Aduckdb.org", url)


if __name__ == "__main__":
    unittest.main()
