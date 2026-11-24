"""
Track Changes & Revision Control Engine — Zye Day 21.
Monitors revisions, inspects change history, and gates bulk acceptance/rejection with confirmation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from zye_office.models.word_models import WordRevisionItem
from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_errors import (
    WordNoActiveDocumentError,
    WordRevisionConfirmationRequiredError,
    WordRevisionNotFoundError,
)

logger = logging.getLogger("zye.office.word.track_changes")


class WordTrackChangesEngine:
    """Controls Track Changes states, revision queries, and individual/bulk review decisions."""

    def __init__(self, adapter: Optional[WordAdapter] = None) -> None:
        self.adapter = adapter or WordAdapter()

    def get_track_changes_status(self) -> Dict[str, Any]:
        """Queries whether Track Changes is actively logging revisions."""
        def _sta_status() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            enabled = getattr(doc, "TrackRevisions", False)
            rev_count = doc.Revisions.Count if hasattr(doc, "Revisions") else 0
            return {
                "status": "SUCCESS",
                "track_changes_enabled": enabled,
                "revision_count": rev_count,
            }

        return self.adapter.worker.run(_sta_status)

    def set_track_changes(self, enabled: bool) -> Dict[str, Any]:
        """Enables or disables Track Changes recording."""
        def _sta_set() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            doc.TrackRevisions = enabled
            return {
                "status": "SUCCESS",
                "track_changes_enabled": doc.TrackRevisions,
                "message": f"Track Changes {'enabled' if enabled else 'disabled'}.",
            }

        return self.adapter.worker.run(_sta_set)

    def get_document_revisions(self, max_count: int = 50) -> Dict[str, Any]:
        """Lists pending revisions with author, date, and bounded preview snippets."""
        def _sta_revisions() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            rev_coll = doc.Revisions
            count = getattr(rev_coll, "Count", len(rev_coll) if isinstance(rev_coll, (list, tuple)) else 0)
            revs: List[Dict[str, Any]] = []
            for i in range(1, min(count + 1, max_count + 1)):
                try:
                    r = rev_coll(i) if callable(rev_coll) else (rev_coll[i-1] if isinstance(rev_coll, (list, tuple)) else getattr(rev_coll, str(i), None))
                    revs.append(
                        WordRevisionItem(
                            index=i,
                            author=getattr(r, "Author", "Unknown"),
                            date=str(getattr(r, "Date", "")),
                            revision_type=str(getattr(r, "Type", "edit")),
                            text_snippet=getattr(getattr(r, "Range", None), "Text", "")[:80].strip(),
                        ).model_dump()
                    )
                except Exception:
                    pass

            return {"status": "SUCCESS", "total_revisions": count, "revisions_count": count, "revisions": revs}

        return self.adapter.worker.run(_sta_revisions)

    def accept_revision(self, revision_id: int) -> Dict[str, Any]:
        """Accepts a single specific 1-based revision."""
        def _sta_accept() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            if revision_id < 1 or revision_id > doc.Revisions.Count:
                raise WordRevisionNotFoundError(f"Revision index {revision_id} does not exist.")

            r = doc.Revisions(revision_id)
            r.Accept()
            return {
                "status": "SUCCESS",
                "accepted_revision": revision_id,
                "remaining_revisions": doc.Revisions.Count,
                "message": f"Accepted revision {revision_id}.",
            }

        return self.adapter.worker.run(_sta_accept)

    def reject_revision(self, revision_id: int) -> Dict[str, Any]:
        """Rejects a single specific 1-based revision."""
        def _sta_reject() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            if revision_id < 1 or revision_id > doc.Revisions.Count:
                raise WordRevisionNotFoundError(f"Revision index {revision_id} does not exist.")

            r = doc.Revisions(revision_id)
            r.Reject()
            return {
                "status": "SUCCESS",
                "rejected_revision": revision_id,
                "remaining_revisions": doc.Revisions.Count,
                "message": f"Rejected revision {revision_id}.",
            }

        return self.adapter.worker.run(_sta_reject)

    def accept_all_revisions(self, confirmed: bool = False) -> Dict[str, Any]:
        """Bulk accepts all revisions. Gated by explicit confirmation."""
        if not confirmed:
            raise WordRevisionConfirmationRequiredError(
                "Accepting ALL revisions removes change history and transforms document content. Pass confirmed=True to proceed."
            )

        def _sta_accept_all() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            initial = doc.Revisions.Count
            doc.Revisions.AcceptAll()
            return {
                "status": "SUCCESS",
                "revisions_accepted": initial,
                "remaining_revisions": doc.Revisions.Count,
                "message": f"Accepted all {initial} revisions.",
            }

        return self.adapter.worker.run(_sta_accept_all)

    def reject_all_revisions(self, confirmed: bool = False) -> Dict[str, Any]:
        """Bulk rejects all revisions. Gated by explicit confirmation."""
        if not confirmed:
            raise WordRevisionConfirmationRequiredError(
                "Rejecting ALL revisions discards all proposed edits. Pass confirmed=True to proceed."
            )

        def _sta_reject_all() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            initial = doc.Revisions.Count
            doc.Revisions.RejectAll()
            return {
                "status": "SUCCESS",
                "revisions_rejected": initial,
                "remaining_revisions": doc.Revisions.Count,
                "message": f"Rejected all {initial} revisions.",
            }

        return self.adapter.worker.run(_sta_reject_all)

    get_revisions = get_document_revisions


WordTrackChangesManager = WordTrackChangesEngine
