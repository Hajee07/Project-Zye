"""
Page Layout Engine — Zye Day 21.
Configures orientation, standard paper sizes (A4, Letter, Legal, A3), margins, and newspaper columns.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_constants import (
    WD_ORIENT_LANDSCAPE,
    WD_ORIENT_PORTRAIT,
    WD_PAPER_A3,
    WD_PAPER_A4,
    WD_PAPER_LEGAL,
    WD_PAPER_LETTER,
)
from zye_office.word.word_errors import WordNoActiveDocumentError, WordLayoutOperationError

logger = logging.getLogger("zye.office.word.layout")

PAPER_SIZE_MAP = {
    "A4": WD_PAPER_A4,
    "LETTER": WD_PAPER_LETTER,
    "LEGAL": WD_PAPER_LEGAL,
    "A3": WD_PAPER_A3,
}


class WordPageLayoutEngine:
    """Configures page geometry, orientation, paper size, margins, and column layouts."""

    def __init__(self, adapter: Optional[WordAdapter] = None) -> None:
        self.adapter = adapter or WordAdapter()

    def set_page_orientation(
        self,
        orientation: str = "PORTRAIT",
        section_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Sets Portrait or Landscape orientation for a specific section or entire document."""
        orient_code = WD_ORIENT_LANDSCAPE if orientation.upper().strip() == "LANDSCAPE" else WD_ORIENT_PORTRAIT

        def _sta_orient() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            if section_index is not None and 1 <= section_index <= doc.Sections.Count:
                doc.Sections(section_index).PageSetup.Orientation = orient_code
                target = f"Section {section_index}"
            else:
                doc.PageSetup.Orientation = orient_code
                target = "Entire document"

            return {
                "status": "SUCCESS",
                "orientation": orientation.upper(),
                "target": target,
                "message": f"Orientation set to {orientation.upper()} for {target}.",
            }

        return self.adapter.worker.run(_sta_orient)

    def set_paper_size(
        self,
        paper_size: str = "A4",
        section_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Sets paper size (A4, Letter, Legal, A3)."""
        norm_size = paper_size.upper().strip()
        if norm_size not in PAPER_SIZE_MAP:
            raise WordLayoutOperationError(f"Paper size '{paper_size}' is invalid. Allowed: {list(PAPER_SIZE_MAP.keys())}")
        code = PAPER_SIZE_MAP[norm_size]

        def _sta_paper() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            if section_index is not None and 1 <= section_index <= doc.Sections.Count:
                doc.Sections(section_index).PageSetup.PaperSize = code
                target = f"Section {section_index}"
            else:
                doc.PageSetup.PaperSize = code
                target = "Entire document"

            return {
                "status": "SUCCESS",
                "paper_size": norm_size,
                "target": target,
                "message": f"Paper size set to {norm_size} for {target}.",
            }

        return self.adapter.worker.run(_sta_paper)

    def set_page_margins(
        self,
        top_pt: Optional[float] = None,
        bottom_pt: Optional[float] = None,
        left_pt: Optional[float] = None,
        right_pt: Optional[float] = None,
        top: Optional[float] = None,
        bottom: Optional[float] = None,
        left: Optional[float] = None,
        right: Optional[float] = None,
        section_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Sets margin dimensions in points (72 points = 1 inch)."""
        eff_top = top if top is not None else top_pt
        eff_bottom = bottom if bottom is not None else bottom_pt
        eff_left = left if left is not None else left_pt
        eff_right = right if right is not None else right_pt

        def _sta_margins() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            setup = doc.Sections(section_index).PageSetup if (section_index and 1 <= section_index <= doc.Sections.Count) else doc.PageSetup

            if eff_top is not None:
                setup.TopMargin = eff_top
            if eff_bottom is not None:
                setup.BottomMargin = eff_bottom
            if eff_left is not None:
                setup.LeftMargin = eff_left
            if eff_right is not None:
                setup.RightMargin = eff_right

            return {
                "status": "SUCCESS",
                "margins": {
                    "top": setup.TopMargin,
                    "bottom": setup.BottomMargin,
                    "left": setup.LeftMargin,
                    "right": setup.RightMargin,
                },
                "message": "Page margins updated successfully.",
            }

        return self.adapter.worker.run(_sta_margins)

    def set_page_columns(
        self,
        columns: int = 1,
        spacing_pt: float = 18.0,
        section_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Configures newspaper column layout (e.g. 1, 2, or 3 columns)."""
        def _sta_columns() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            setup = doc.Sections(section_index).PageSetup if (section_index and 1 <= section_index <= doc.Sections.Count) else doc.PageSetup
            setup.TextColumns.SetCount(columns)
            if columns > 1:
                setup.TextColumns.Spacing = spacing_pt

            return {
                "status": "SUCCESS",
                "columns": columns,
                "spacing_pt": spacing_pt,
                "message": f"Configured {columns} column(s).",
            }

        return self.adapter.worker.run(_sta_columns)


WordPageLayoutManager = WordPageLayoutEngine
