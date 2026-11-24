"""
Section Management Engine — Zye Day 21.
Handles section creation, section counts, and header/footer linkage isolation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_constants import WD_SECTION_BREAK_NEXT_PAGE
from zye_office.word.word_errors import WordNoActiveDocumentError

logger = logging.getLogger("zye.office.word.sections")


class WordSectionManager:
    """Manages document sections, boundaries, and link-to-previous states."""

    def __init__(self, adapter: Optional[WordAdapter] = None) -> None:
        self.adapter = adapter or WordAdapter()

    def get_document_sections(self) -> Dict[str, Any]:
        """Inspects all sections in the active document."""
        def _sta_sections() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            count = doc.Sections.Count
            sec_details = []
            for i in range(1, count + 1):
                try:
                    s = doc.Sections(i)
                    sec_details.append({
                        "index": i,
                        "orientation": "LANDSCAPE" if s.PageSetup.Orientation == 1 else "PORTRAIT",
                        "top_margin": s.PageSetup.TopMargin,
                        "bottom_margin": s.PageSetup.BottomMargin,
                        "left_margin": s.PageSetup.LeftMargin,
                        "right_margin": s.PageSetup.RightMargin,
                    })
                except Exception:
                    pass

            return {"status": "SUCCESS", "total_sections": count, "sections": sec_details}

        return self.adapter.worker.run(_sta_sections)

    def create_document_section(self, break_type: int = WD_SECTION_BREAK_NEXT_PAGE) -> Dict[str, Any]:
        """Adds a section break at document end or current selection."""
        def _sta_add_sec() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            app.Selection.InsertBreak(Type=break_type)
            return {
                "status": "SUCCESS",
                "new_total_sections": doc.Sections.Count,
                "message": f"Section break inserted. Document now has {doc.Sections.Count} sections.",
            }

        return self.adapter.worker.run(_sta_add_sec)

    def unlink_header_from_previous(self, section_index: int) -> Dict[str, Any]:
        """Breaks LinkToPrevious connection for headers in specified section."""
        def _sta_unlink() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            if section_index <= 1 or section_index > doc.Sections.Count:
                return {"status": "SKIPPED", "message": "Cannot unlink Section 1 or invalid index."}

            sec = doc.Sections(section_index)
            sec.Headers(1).LinkToPrevious = False
            sec.Footers(1).LinkToPrevious = False
            return {
                "status": "SUCCESS",
                "section": section_index,
                "link_to_previous": False,
                "message": f"Section {section_index} unlinked from previous header/footer.",
            }

        return self.adapter.worker.run(_sta_unlink)

    insert_section_break = create_document_section
