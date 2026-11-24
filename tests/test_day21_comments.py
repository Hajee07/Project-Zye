"""
Day 21 Unit Tests — Word Review Comments Engine.
Verifies review comment creation, author tagging, comment inspection, resolution, and deletion.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_office.word.word_comment_engine import WordCommentEngine
from zye_office.word.word_errors import WordNoActiveDocumentError


class TestDay21Comments(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_adapter = MagicMock()
        self.mock_adapter.worker.run.side_effect = lambda fn: fn()
        self.engine = WordCommentEngine(adapter=self.mock_adapter)

    def test_add_comment(self) -> None:
        """Verify adding a review comment to selection."""
        mock_doc = MagicMock()
        mock_app = MagicMock()
        mock_comments = MagicMock()
        mock_doc.Comments = mock_comments
        mock_comments.Count = 1
        self.mock_adapter.get_raw_app.return_value = mock_app
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.add_comment(
            comment_text="Please verify the financial table metrics.",
            author="Zye AI Assistant",
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["author"], "Zye AI Assistant")
        mock_comments.Add.assert_called_once()

    def test_get_document_comments(self) -> None:
        """Verify querying active comments."""
        mock_doc = MagicMock()
        mock_c = MagicMock()
        mock_c.Author = "Zye AI Assistant"
        mock_c.Date = "2026-11-20"
        mock_c.Range.Text = "Review required.\r"
        mock_c.Scope.Text = "Target text"
        mock_c.Resolved = False
        mock_doc.Comments = [mock_c]
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.get_comments()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["count"], 1)
        self.assertEqual(res["comments"][0]["author"], "Zye AI Assistant")

    def test_resolve_comment(self) -> None:
        """Verify resolving a comment index."""
        mock_doc = MagicMock()
        mock_c = MagicMock()
        mock_doc.Comments.Count = 1
        mock_doc.Comments.return_value = mock_c
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.resolve_comment(comment_id=1, resolved=True)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(mock_c.Resolved)

    def test_delete_comment(self) -> None:
        """Verify deleting a comment."""
        mock_doc = MagicMock()
        mock_c = MagicMock()
        mock_doc.Comments.Count = 1
        mock_doc.Comments.return_value = mock_c
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.delete_comment(comment_id=1)
        self.assertEqual(res["status"], "SUCCESS")
        mock_c.Delete.assert_called_once()


if __name__ == "__main__":
    unittest.main()
