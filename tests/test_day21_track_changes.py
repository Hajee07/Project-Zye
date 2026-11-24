"""
Day 21 Unit Tests — Word Track Changes Engine.
Verifies tracking toggle, revision inspection, individual accept/reject, and confirmation gating on bulk actions.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_office.word.word_errors import (
    WordNoActiveDocumentError,
    WordRevisionConfirmationRequiredError,
    WordRevisionNotFoundError,
)
from zye_office.word.word_track_changes import WordTrackChangesEngine, WordTrackChangesManager


class TestDay21TrackChanges(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_adapter = MagicMock()
        self.mock_adapter.worker.run.side_effect = lambda fn: fn()
        self.engine = WordTrackChangesManager(adapter=self.mock_adapter)

    def test_set_track_changes_toggle(self) -> None:
        """Verify enabling and disabling Track Changes."""
        mock_doc = MagicMock()
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.set_track_changes(enabled=True)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(mock_doc.TrackRevisions)

        res2 = self.engine.set_track_changes(enabled=False)
        self.assertEqual(res2["status"], "SUCCESS")
        self.assertFalse(mock_doc.TrackRevisions)

    def test_get_document_revisions(self) -> None:
        """Verify listing revisions in document."""
        mock_doc = MagicMock()
        mock_rev = MagicMock()
        mock_rev.Author = "Lead Architect"
        mock_rev.Date = "2026-11-20"
        mock_rev.Type = 1  # wdRevisionInsert
        mock_rev.Range.Text = "Newly inserted paragraph text"
        mock_doc.Revisions = [mock_rev]
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.get_revisions()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["revisions_count"], 1)
        self.assertEqual(res["revisions"][0]["author"], "Lead Architect")

    def test_accept_revision_by_index(self) -> None:
        """Verify accepting a single revision."""
        mock_doc = MagicMock()
        mock_rev = MagicMock()
        mock_doc.Revisions.Count = 1
        mock_doc.Revisions.return_value = mock_rev
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.accept_revision(revision_id=1)
        self.assertEqual(res["status"], "SUCCESS")
        mock_rev.Accept.assert_called_once()

    def test_accept_all_revisions_requires_confirmation(self) -> None:
        """Verify bulk accepting revisions without confirmed=True raises WordRevisionConfirmationRequiredError."""
        with self.assertRaises(WordRevisionConfirmationRequiredError):
            self.engine.accept_all_revisions(confirmed=False)

    def test_accept_all_revisions_with_confirmation(self) -> None:
        """Verify bulk accepting revisions succeeds when confirmed=True."""
        mock_doc = MagicMock()
        mock_doc.Revisions.Count = 3
        self.mock_adapter.get_active_document_raw.return_value = mock_doc

        res = self.engine.accept_all_revisions(confirmed=True)
        self.assertEqual(res["status"], "SUCCESS")
        mock_doc.Revisions.AcceptAll.assert_called_once()

    def test_reject_all_revisions_requires_confirmation(self) -> None:
        """Verify bulk rejecting revisions without confirmed=True raises WordRevisionConfirmationRequiredError."""
        with self.assertRaises(WordRevisionConfirmationRequiredError):
            self.engine.reject_all_revisions(confirmed=False)


if __name__ == "__main__":
    unittest.main()
