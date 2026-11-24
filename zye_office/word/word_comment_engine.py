"""
Comments Engine — Zye Day 21.
Creates, inspects, resolves, and manages annotation comments on Word documents.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from zye_office.models.word_models import WordCommentItem
from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_errors import WordNoActiveDocumentError
from zye_office.word.word_validator import WordValidator

logger = logging.getLogger("zye.office.word.comments")


class WordCommentEngine:
    """Manages document comments and margin annotations."""

    def __init__(
        self,
        adapter: Optional[WordAdapter] = None,
        validator: Optional[WordValidator] = None,
    ) -> None:
        self.adapter = adapter or WordAdapter()
        self.validator = validator or WordValidator()

    def add_comment(
        self,
        text: str = "",
        target_range: Optional[Any] = None,
        comment_text: Optional[str] = None,
        author: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Attaches an annotation comment to the current selection or range."""
        raw_text = comment_text if comment_text is not None else text
        clean_text = self.validator.validate_unicode_text(raw_text)

        def _sta_add_comment() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            rng = target_range or app.Selection.Range
            comm = doc.Comments.Add(Range=rng, Text=clean_text)
            if author and hasattr(comm, "Author"):
                try:
                    comm.Author = author
                except Exception:
                    pass

            return {
                "status": "SUCCESS",
                "comment_index": getattr(comm, "Index", 1),
                "text": clean_text,
                "author": author or getattr(comm, "Author", "Zye"),
                "message": "Comment added successfully.",
            }

        return self.adapter.worker.run(_sta_add_comment)

    def get_document_comments(self) -> Dict[str, Any]:
        """Lists all comments currently attached to the document."""
        def _sta_get_comments() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            comm_coll = doc.Comments
            count = getattr(comm_coll, "Count", len(comm_coll) if isinstance(comm_coll, (list, tuple)) else 0)
            comments_list: List[Dict[str, Any]] = []
            for i in range(1, count + 1):
                try:
                    c = comm_coll(i) if callable(comm_coll) else (comm_coll[i-1] if isinstance(comm_coll, (list, tuple)) else getattr(comm_coll, str(i), None))
                    comments_list.append(
                        WordCommentItem(
                            index=i,
                            author=getattr(c, "Author", ""),
                            date=str(getattr(c, "Date", "")),
                            text=getattr(getattr(c, "Range", None), "Text", "").strip(),
                            resolved=getattr(c, "Done", getattr(c, "Resolved", False)),
                            scope_text=getattr(getattr(c, "Scope", None), "Text", "")[:50].strip(),
                        ).model_dump()
                    )
                except Exception:
                    pass

            return {"status": "SUCCESS", "count": count, "comments": comments_list}

        return self.adapter.worker.run(_sta_get_comments)

    def resolve_comment(self, comment_id: int, resolved: bool = True) -> Dict[str, Any]:
        """Marks a comment as resolved / done if supported by Word version."""
        def _sta_resolve() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            comm_coll = doc.Comments
            count = getattr(comm_coll, "Count", len(comm_coll) if isinstance(comm_coll, (list, tuple)) else 0)
            if comment_id < 1 or comment_id > count:
                return {"status": "NOT_FOUND", "message": f"Comment {comment_id} does not exist."}

            comm = comm_coll(comment_id) if callable(comm_coll) else (comm_coll[comment_id-1] if isinstance(comm_coll, (list, tuple)) else None)
            if comm and hasattr(comm, "Done"):
                comm.Done = resolved
                status_msg = f"Comment {comment_id} resolved state set to {resolved}."
            elif comm and hasattr(comm, "Resolved"):
                comm.Resolved = resolved
                status_msg = f"Comment {comment_id} resolved state set to {resolved}."
            else:
                status_msg = f"Comment {comment_id} does not support Done attribute on this Word version."

            return {"status": "SUCCESS", "comment_index": comment_id, "message": status_msg}

        return self.adapter.worker.run(_sta_resolve)

    def delete_comment(self, comment_id: int) -> Dict[str, Any]:
        """Deletes a specific comment."""
        def _sta_del() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            if comment_id < 1 or comment_id > doc.Comments.Count:
                return {"status": "NOT_FOUND", "message": f"Comment {comment_id} does not exist."}

            doc.Comments(comment_id).Delete()
            return {"status": "SUCCESS", "deleted_comment": comment_id, "message": f"Comment {comment_id} deleted."}

        return self.adapter.worker.run(_sta_del)

    get_comments = get_document_comments
