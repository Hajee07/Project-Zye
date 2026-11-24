"""
Automatic Table of Contents (TOC) Engine — Zye Day 21.
Generates, inspects, and refreshes dynamic Table of Contents fields from heading hierarchy.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_errors import WordNoActiveDocumentError, WordValidationError

logger = logging.getLogger("zye.office.word.toc")


class WordTOCEngine:
    """Manages creation, heading hierarchy analysis, and updates for Table of Contents."""

    def __init__(self, adapter: Optional[WordAdapter] = None) -> None:
        self.adapter = adapter or WordAdapter()

    def inspect_heading_hierarchy(self) -> Dict[str, Any]:
        """Checks for presence of Heading 1..3 styles in the document."""
        def _sta_inspect_headings() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            headings_found = []
            for p in doc.Paragraphs:
                try:
                    style_obj = getattr(getattr(p, "Range", None), "Style", getattr(p, "Style", None))
                    s_name = str(getattr(style_obj, "NameLocal", ""))
                    if "heading" in s_name.lower():
                        lvl = 1
                        parts = s_name.split()
                        if parts and parts[-1].isdigit():
                            lvl = int(parts[-1])
                        headings_found.append({
                            "style": s_name,
                            "level": lvl,
                            "text": p.Range.Text.strip()[:80],
                        })
                except Exception:
                    pass

            return {
                "status": "SUCCESS",
                "total_headings": len(headings_found),
                "heading_count": len(headings_found),
                "headings": headings_found[:30],
                "has_usable_hierarchy": len(headings_found) > 0,
            }

        return self.adapter.worker.run(_sta_inspect_headings)

    def insert_table_of_contents(
        self,
        upper_level: int = 1,
        lower_level: int = 3,
        use_heading_styles: bool = True,
    ) -> Dict[str, Any]:
        """Inserts an automated Table of Contents at the start or current selection."""
        if upper_level < 1 or lower_level > 9 or upper_level > lower_level:
            raise WordValidationError(
                f"Invalid TOC levels: upper_level={upper_level}, lower_level={lower_level}. Must be 1 <= upper <= lower <= 9."
            )
        hierarchy = self.inspect_heading_hierarchy()

        def _sta_add_toc() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            rng = app.Selection.Range
            toc = doc.TablesOfContents.Add(
                Range=rng,
                UseHeadingStyles=use_heading_styles,
                UpperHeadingLevel=upper_level,
                LowerHeadingLevel=lower_level,
                IncludePageNumbers=True,
                RightAlignPageNumbers=True,
            )

            return {
                "status": "SUCCESS",
                "upper_level": upper_level,
                "lower_level": lower_level,
                "toc_count": doc.TablesOfContents.Count,
                "headings_detected": hierarchy.get("total_headings", 0),
                "has_headings": hierarchy.get("has_usable_hierarchy", False),
                "message": "Table of Contents generated.",
            }

        return self.adapter.worker.run(_sta_add_toc)

    def update_table_of_contents(self) -> Dict[str, Any]:
        """Refreshes all Table of Contents fields in the active document."""
        def _sta_update_toc() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            if doc.TablesOfContents.Count == 0:
                return {
                    "status": "NOT_FOUND",
                    "message": "No Table of Contents found in document to update.",
                }

            for i in range(1, doc.TablesOfContents.Count + 1):
                try:
                    doc.TablesOfContents(i).Update()
                except Exception as exc:
                    logger.warning("Error updating TOC %d: %s", i, exc)

            return {
                "status": "SUCCESS",
                "updated_count": doc.TablesOfContents.Count,
                "message": "Table of Contents updated.",
            }

        return self.adapter.worker.run(_sta_update_toc)

    insert_toc = insert_table_of_contents
    update_toc = update_table_of_contents
