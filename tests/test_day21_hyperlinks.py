"""
Day 21 Unit Tests — Word Hyperlink Engine.
Verifies hyperlink insertion, safe URL protocol validation (HTTP/HTTPS allowed; javascript:, file:, data: blocked),
and active hyperlink queries.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_office.word.word_errors import WordNoActiveDocumentError, WordSecurityError, WordValidationError
from zye_office.word.word_hyperlink_engine import WordHyperlinkEngine


class TestDay21Hyperlinks(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_adapter = MagicMock()
        self.mock_adapter.worker.run.side_effect = lambda fn: fn()
        self.engine = WordHyperlinkEngine(adapter=self.mock_adapter)

    def test_insert_hyperlink_valid_https(self) -> None:
        """Verify inserting valid HTTPS hyperlink."""
        mock_doc = MagicMock()
        mock_links = MagicMock()
        mock_doc.Hyperlinks = mock_links
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.insert_hyperlink(
            address="https://github.com/google/gemini",
            display_text="Gemini Official Repository",
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["address"], "https://github.com/google/gemini")
        mock_links.Add.assert_called_once()

    def test_insert_hyperlink_dangerous_scheme_blocked(self) -> None:
        """Verify dangerous URL protocols (javascript, vbscript, file, data) are blocked with WordSecurityError."""
        dangerous_urls = [
            "javascript:alert(1)",
            "vbscript:msgbox(1)",
            "file:///C:/Windows/System32/cmd.exe",
            "data:text/html,<script>alert(1)</script>",
        ]
        for url in dangerous_urls:
            with self.assertRaises(WordSecurityError):
                self.engine.insert_hyperlink(address=url, display_text="Malicious Link")

    def test_get_document_hyperlinks(self) -> None:
        """Verify querying list of hyperlinks in document."""
        mock_doc = MagicMock()
        mock_link = MagicMock()
        mock_link.Address = "https://example.com"
        mock_link.TextToDisplay = "Example Site"
        mock_doc.Hyperlinks = [mock_link]
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.get_document_hyperlinks()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["count"], 1)
        self.assertEqual(res["hyperlinks"][0]["address"], "https://example.com")


if __name__ == "__main__":
    unittest.main()
