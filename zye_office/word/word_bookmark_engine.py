"""
Bookmark Engine — Zye Day 21.
Creates, navigates to, lists, and removes named bookmarks in Microsoft Word.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_errors import WordNoActiveDocumentError, WordValidationError

logger = logging.getLogger("zye.office.word.bookmarks")


class WordBookmarkEngine:
    """Manages document bookmarks for cross-referencing and rapid cursor navigation."""

    def __init__(self, adapter: Optional[WordAdapter] = None) -> None:
        self.adapter = adapter or WordAdapter()

    def validate_bookmark_name(self, name: str) -> str:
        clean = (name or "").strip()
        if not re.match(r"^[A-Za-z][A-Za-z0-9_]{0,39}$", clean):
            raise WordValidationError(
                f"Bookmark name '{clean}' is invalid. Must start with a letter and contain only alphanumeric characters and underscores (max 40 chars)."
            )
        return clean

    def create_bookmark(self, name: str, target_range: Optional[Any] = None) -> Dict[str, Any]:
        """Creates a bookmark at current selection or target range."""
        valid_name = self.validate_bookmark_name(name)

        def _sta_add_bm() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            rng = target_range or app.Selection.Range
            doc.Bookmarks.Add(Name=valid_name, Range=rng)

            return {
                "status": "SUCCESS",
                "bookmark_name": valid_name,
                "message": f"Bookmark '{valid_name}' created.",
            }

        return self.adapter.worker.run(_sta_add_bm)

    def get_bookmarks(self) -> Dict[str, Any]:
        """Returns all named bookmarks defined in the active document."""
        def _sta_get_bms() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            bms = []
            bm_coll = doc.Bookmarks
            bm_count = getattr(bm_coll, "Count", len(bm_coll) if isinstance(bm_coll, (list, tuple)) else 0)
            for i in range(1, bm_count + 1):
                try:
                    bm = bm_coll(i) if callable(bm_coll) else (bm_coll[i-1] if isinstance(bm_coll, (list, tuple)) else getattr(bm_coll, str(i), None))
                    bms.append({
                        "name": getattr(bm, "Name", ""),
                        "text_preview": getattr(getattr(bm, "Range", None), "Text", "")[:50].strip(),
                    })
                except Exception:
                    pass

            return {"status": "SUCCESS", "count": len(bms), "bookmarks": bms}

        return self.adapter.worker.run(_sta_get_bms)

    def delete_bookmark(self, name: str) -> Dict[str, Any]:
        """Deletes a named bookmark."""
        valid_name = self.validate_bookmark_name(name)

        def _sta_del_bm() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            if not doc.Bookmarks.Exists(valid_name):
                return {"status": "NOT_FOUND", "message": f"Bookmark '{valid_name}' does not exist."}

            doc.Bookmarks(valid_name).Delete()
            return {"status": "SUCCESS", "bookmark_name": valid_name, "message": f"Bookmark '{valid_name}' deleted."}

        return self.adapter.worker.run(_sta_del_bm)

    get_document_bookmarks = get_bookmarks
