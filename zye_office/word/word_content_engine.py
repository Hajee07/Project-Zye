"""
Advanced Content Editing Engine — Zye Day 21.
Handles range-based text insertion, paragraph structures, exact and bulk replacement,
deletions, breaks, and date/page fields with Unicode & Tamil text preservation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_constants import (
    WD_FIELD_DATE,
    WD_FIELD_PAGE,
    WD_LINE_BREAK,
    WD_PAGE_BREAK,
    WD_SECTION_BREAK_NEXT_PAGE,
)
from zye_office.word.word_errors import (
    WordInvalidRangeError,
    WordNoActiveDocumentError,
    WordTextNotFoundError,
)
from zye_office.word.word_validator import WordValidator

logger = logging.getLogger("zye.office.word.content")


class WordContentEngine:
    """Range-safe text insertion, replacement, deletion, and structural break engine."""

    def __init__(
        self,
        adapter: Optional[WordAdapter] = None,
        validator: Optional[WordValidator] = None,
    ) -> None:
        self.adapter = adapter or WordAdapter()
        self.validator = validator or WordValidator()

    def insert_text(
        self,
        text: str,
        location: str = "end",  # end, start, selection, or paragraph
    ) -> Dict[str, Any]:
        """Insert text at specified document boundary with full Unicode fidelity."""
        clean_text = self.validator.validate_unicode_text(text)

        def _sta_insert() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            loc = location.strip().lower()
            if loc == "end":
                rng = doc.Content
                rng.Collapse(0)  # wdCollapseEnd = 0
                rng.InsertAfter(clean_text)
            elif loc == "start":
                rng = doc.Range(0, 0)
                rng.InsertBefore(clean_text)
            elif loc == "selection":
                sel = app.Selection
                sel.TypeText(clean_text)
            else:
                doc.Content.InsertAfter(clean_text)

            return {
                "status": "SUCCESS",
                "location": loc,
                "text": clean_text,
                "chars_inserted": len(clean_text),
                "message": f"Inserted {len(clean_text)} characters at '{loc}'.",
            }

        return self.adapter.worker.run(_sta_insert)

    def insert_paragraph(
        self,
        text: str,
        location: str = "end",
    ) -> Dict[str, Any]:
        """Insert a standalone paragraph terminated by paragraph break."""
        clean_text = self.validator.validate_unicode_text(text)

        def _sta_insert_para() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            loc = location.strip().lower()
            if loc == "start":
                p = doc.Paragraphs.Add(doc.Range(0, 0))
                p.Range.Text = clean_text + "\n"
            else:
                rng = doc.Content
                rng.Collapse(0)
                p = doc.Paragraphs.Add(rng)
                p.Range.Text = clean_text + "\n"

            return {
                "status": "SUCCESS",
                "location": loc,
                "text": clean_text,
                "message": "Paragraph added successfully.",
            }

        return self.adapter.worker.run(_sta_insert_para)

    def replace_exact_text(
        self,
        old_text: str,
        new_text: str,
        replace_all: bool = False,
    ) -> Dict[str, Any]:
        """Find and replace text using Word's native Find and Replace engine."""
        clean_old = self.validator.validate_unicode_text(old_text)
        clean_new = self.validator.validate_unicode_text(new_text)

        def _sta_replace() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            find_obj = doc.Content.Find
            find_obj.ClearFormatting()
            find_obj.Replacement.ClearFormatting()

            # wdReplaceOne = 1, wdReplaceAll = 2
            replace_mode = 2 if replace_all else 1
            executed = find_obj.Execute(
                FindText=clean_old,
                MatchCase=False,
                MatchWholeWord=False,
                MatchWildcards=False,
                ReplaceWith=clean_new,
                Replace=replace_mode,
            )

            if not executed and not replace_all:
                raise WordTextNotFoundError(f"Target text '{clean_old}' not found in document.")

            return {
                "status": "SUCCESS",
                "replaced": executed,
                "old_text": clean_old,
                "new_text": clean_new,
                "replace_all": replace_all,
                "message": f"Text replacement completed (found and replaced: {executed}).",
            }

        return self.adapter.worker.run(_sta_replace)

    replace_text = replace_exact_text

    def delete_selected_text(self) -> Dict[str, Any]:
        """Delete currently selected text in active Word window."""
        def _sta_delete() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            if app is None or self.adapter.get_active_document_raw() is None:
                raise WordNoActiveDocumentError()

            sel = app.Selection
            deleted_chars = len(sel.Text)
            sel.Delete()
            return {
                "status": "SUCCESS",
                "deleted_chars": deleted_chars,
                "message": f"Deleted {deleted_chars} characters from selection.",
            }

        return self.adapter.worker.run(_sta_delete)

    def insert_page_break(self) -> Dict[str, Any]:
        """Insert a hard page break at the current selection / cursor position."""
        def _sta_page_break() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            if app is None or self.adapter.get_active_document_raw() is None:
                raise WordNoActiveDocumentError()

            app.Selection.InsertBreak(Type=WD_PAGE_BREAK)
            return {"status": "SUCCESS", "break_type": "PAGE_BREAK", "message": "Page break inserted."}

        return self.adapter.worker.run(_sta_page_break)

    def insert_section_break(self, break_type: int = WD_SECTION_BREAK_NEXT_PAGE) -> Dict[str, Any]:
        """Insert a section break (e.g. Next Page or Continuous)."""
        def _sta_section_break() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            if app is None or self.adapter.get_active_document_raw() is None:
                raise WordNoActiveDocumentError()

            app.Selection.InsertBreak(Type=break_type)
            doc = self.adapter.get_active_document_raw()
            total_sec = getattr(getattr(doc, "Sections", None), "Count", 2)
            return {
                "status": "SUCCESS",
                "break_type": "SECTION_BREAK",
                "code": break_type,
                "new_total_sections": total_sec,
                "message": "Section break inserted.",
            }

        return self.adapter.worker.run(_sta_section_break)

    def insert_field(self, field_type: int = WD_FIELD_DATE) -> Dict[str, Any]:
        """Insert dynamic document fields (Date, Page Number, etc.)."""
        def _sta_field() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            if app is None or self.adapter.get_active_document_raw() is None:
                raise WordNoActiveDocumentError()

            doc = self.adapter.get_active_document_raw()
            field = doc.Fields.Add(Range=app.Selection.Range, Type=field_type)
            return {
                "status": "SUCCESS",
                "field_type": field_type,
                "field_result": getattr(field.Result, "Text", ""),
                "message": "Field inserted.",
            }

        return self.adapter.worker.run(_sta_field)
