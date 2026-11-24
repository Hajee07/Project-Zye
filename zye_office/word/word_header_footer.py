"""
Headers and Footers Engine — Zye Day 21.
Configures primary, first-page, and odd/even headers and footers,
page numbering fields, total pages count, and section-specific linkages.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_constants import (
    WD_ALIGN_PARAGRAPH_CENTER,
    WD_ALIGN_PARAGRAPH_LEFT,
    WD_ALIGN_PARAGRAPH_RIGHT,
    WD_FIELD_NUM_PAGES,
    WD_FIELD_PAGE,
    WD_HEADER_FOOTER_FIRST_PAGE,
    WD_HEADER_FOOTER_PRIMARY,
)
from zye_office.word.word_errors import WordNoActiveDocumentError
from zye_office.word.word_validator import WordValidator

logger = logging.getLogger("zye.office.word.headers_footers")


class WordHeaderFooterEngine:
    """Controls primary, first-page, section-specific headers, footers, and page numbering."""

    def __init__(
        self,
        adapter: Optional[WordAdapter] = None,
        validator: Optional[WordValidator] = None,
    ) -> None:
        self.adapter = adapter or WordAdapter()
        self.validator = validator or WordValidator()

    def set_document_header(
        self,
        text: str,
        section_index: int = 1,
        alignment: str = "center",
    ) -> Dict[str, Any]:
        """Sets text in the primary header of specified document section."""
        clean_text = self.validator.validate_unicode_text(text)
        align_code = self.validator.validate_alignment(alignment) or WD_ALIGN_PARAGRAPH_CENTER

        def _sta_set_header() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            sec = doc.Sections(section_index)
            hdr = sec.Headers(WD_HEADER_FOOTER_PRIMARY)
            hdr.Range.Text = clean_text
            hdr.Range.ParagraphFormat.Alignment = align_code

            return {
                "status": "SUCCESS",
                "section": section_index,
                "header_text": clean_text,
                "alignment": alignment,
                "message": f"Header set on Section {section_index}.",
            }

        return self.adapter.worker.run(_sta_set_header)

    def set_document_footer(
        self,
        text: str,
        section_index: int = 1,
        alignment: str = "center",
    ) -> Dict[str, Any]:
        """Sets text in the primary footer of specified document section."""
        clean_text = self.validator.validate_unicode_text(text)
        align_code = self.validator.validate_alignment(alignment) or WD_ALIGN_PARAGRAPH_CENTER

        def _sta_set_footer() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            sec = doc.Sections(section_index)
            ftr = sec.Footers(WD_HEADER_FOOTER_PRIMARY)
            ftr.Range.Text = clean_text
            ftr.Range.ParagraphFormat.Alignment = align_code

            return {
                "status": "SUCCESS",
                "section": section_index,
                "footer_text": clean_text,
                "alignment": alignment,
                "message": f"Footer set on Section {section_index}.",
            }

        return self.adapter.worker.run(_sta_set_footer)

    def set_different_first_page(
        self,
        enabled: bool = True,
        section_index: int = 1,
        first_page_header_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Configures distinct first-page header/footer behavior."""
        def _sta_diff_first() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            sec = doc.Sections(section_index)
            sec.PageSetup.DifferentFirstPageHeaderFooter = enabled

            if enabled and first_page_header_text:
                clean_hdr = self.validator.validate_unicode_text(first_page_header_text)
                fp_hdr = sec.Headers(WD_HEADER_FOOTER_FIRST_PAGE)
                fp_hdr.Range.Text = clean_hdr

            return {
                "status": "SUCCESS",
                "section": section_index,
                "different_first_page": enabled,
                "message": f"DifferentFirstPageHeaderFooter set to {enabled}.",
            }

        return self.adapter.worker.run(_sta_diff_first)

    def insert_page_numbers(
        self,
        position: str = "footer_right",  # footer_right, footer_center, footer_left, header_right
        section_index: int = 1,
    ) -> Dict[str, Any]:
        """Inserts dynamic PAGE field into footer or header with alignment."""
        align_map = {
            "right": WD_ALIGN_PARAGRAPH_RIGHT,
            "center": WD_ALIGN_PARAGRAPH_CENTER,
            "left": WD_ALIGN_PARAGRAPH_LEFT,
        }
        align_key = position.split("_")[-1] if "_" in position else "right"
        align_code = align_map.get(align_key, WD_ALIGN_PARAGRAPH_RIGHT)
        is_footer = "header" not in position.lower()

        def _sta_page_nums() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            sec = doc.Sections(section_index)
            target = sec.Footers(WD_HEADER_FOOTER_PRIMARY) if is_footer else sec.Headers(WD_HEADER_FOOTER_PRIMARY)

            rng = target.Range
            rng.Collapse(0)  # Collapse to end
            doc.Fields.Add(Range=rng, Type=WD_FIELD_PAGE)
            target.Range.ParagraphFormat.Alignment = align_code

            return {
                "status": "SUCCESS",
                "section": section_index,
                "target": "footer" if is_footer else "header",
                "alignment": align_key,
                "message": f"Page number field added to {'footer' if is_footer else 'header'}.",
            }

        return self.adapter.worker.run(_sta_page_nums)

    set_header = set_document_header
    set_footer = set_document_footer


WordHeaderFooterManager = WordHeaderFooterEngine
