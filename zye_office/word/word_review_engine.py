"""
Document Review & Inspection Engine — Zye Day 21.
Inspects overall review status, markup display modes, and comparison readiness.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_errors import WordNoActiveDocumentError

logger = logging.getLogger("zye.office.word.review")


class WordReviewEngine:
    """Manages document review views, markup display modes, and review statistics."""

    def __init__(self, adapter: Optional[WordAdapter] = None) -> None:
        self.adapter = adapter or WordAdapter()

    def inspect_document_review_state(self) -> Dict[str, Any]:
        """Provides consolidated review state including revisions count and comments count."""
        def _sta_review_state() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            revs_count = doc.Revisions.Count if hasattr(doc, "Revisions") else 0
            comments_count = doc.Comments.Count if hasattr(doc, "Comments") else 0
            track_changes = getattr(doc, "TrackRevisions", False)

            return {
                "status": "SUCCESS",
                "track_changes_enabled": track_changes,
                "revisions_count": revs_count,
                "comments_count": comments_count,
                "has_pending_reviews": (revs_count > 0 or comments_count > 0),
            }

        return self.adapter.worker.run(_sta_review_state)
