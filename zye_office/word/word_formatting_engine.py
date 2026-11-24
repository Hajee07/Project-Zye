"""
Advanced Text & Paragraph Formatting Engine — Zye Day 21.
Applies typography, font styling, colors, paragraph alignments, line and spacing properties.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from zye_office.models.word_models import WordFormatOptions
from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_errors import WordNoActiveDocumentError
from zye_office.word.word_validator import WordValidator

logger = logging.getLogger("zye.office.word.formatting")


class WordFormattingEngine:
    """Range-bounded font and paragraph formatting controller."""

    def __init__(
        self,
        adapter: Optional[WordAdapter] = None,
        validator: Optional[WordValidator] = None,
    ) -> None:
        self.adapter = adapter or WordAdapter()
        self.validator = validator or WordValidator()

    def apply_formatting(
        self,
        options: WordFormatOptions,
        target_range: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Applies typography and paragraph settings to the target range or active Selection."""
        self.validator.validate_font_size(options.font_size)
        align_code = self.validator.validate_alignment(options.alignment)

        def _sta_format() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            rng = target_range or app.Selection.Range

            # Font Formatting
            if options.font_name:
                rng.Font.Name = options.font_name
            if options.font_size:
                rng.Font.Size = options.font_size
            if options.bold is not None:
                rng.Font.Bold = options.bold
            if options.italic is not None:
                rng.Font.Italic = options.italic
            if options.underline is not None:
                rng.Font.Underline = 1 if options.underline else 0
            if options.strikethrough is not None:
                rng.Font.StrikeThrough = options.strikethrough
            if options.subscript is not None:
                rng.Font.Subscript = options.subscript
            if options.superscript is not None:
                rng.Font.Superscript = options.superscript
            if options.color is not None:
                rng.Font.Color = options.color
            if options.highlight is not None:
                rng.HighlightColorIndex = options.highlight

            # Paragraph Formatting
            if align_code is not None:
                rng.ParagraphFormat.Alignment = align_code
            if options.line_spacing is not None:
                rng.ParagraphFormat.LineSpacing = options.line_spacing
            if options.space_before is not None:
                rng.ParagraphFormat.SpaceBefore = options.space_before
            if options.space_after is not None:
                rng.ParagraphFormat.SpaceAfter = options.space_after
            if options.left_indent is not None:
                rng.ParagraphFormat.LeftIndent = options.left_indent
            if options.right_indent is not None:
                rng.ParagraphFormat.RightIndent = options.right_indent
            if options.first_line_indent is not None:
                rng.ParagraphFormat.FirstLineIndent = options.first_line_indent

            return {
                "status": "SUCCESS",
                "applied_options": options.model_dump(exclude_none=True),
                "message": "Formatting applied successfully.",
            }

        return self.adapter.worker.run(_sta_format)

    def set_font_bold(self, bold: bool = True) -> Dict[str, Any]:
        return self.apply_formatting(WordFormatOptions(bold=bold))

    def set_font_italic(self, italic: bool = True) -> Dict[str, Any]:
        return self.apply_formatting(WordFormatOptions(italic=italic))

    def set_font_size(self, size_pt: float) -> Dict[str, Any]:
        return self.apply_formatting(WordFormatOptions(font_size=size_pt))

    def set_paragraph_alignment(self, alignment: str) -> Dict[str, Any]:
        return self.apply_formatting(WordFormatOptions(alignment=alignment))

    format_text = apply_formatting

    def format_paragraph(
        self,
        alignment: Optional[str] = None,
        line_spacing: Optional[float] = None,
        space_before: Optional[float] = None,
        space_after: Optional[float] = None,
        left_indent: Optional[float] = None,
        right_indent: Optional[float] = None,
        first_line_indent: Optional[float] = None,
    ) -> Dict[str, Any]:
        opts = WordFormatOptions(
            alignment=alignment,
            line_spacing=line_spacing,
            space_before=space_before,
            space_after=space_after,
            left_indent=left_indent,
            right_indent=right_indent,
            first_line_indent=first_line_indent,
        )
        res = self.apply_formatting(opts)
        res["alignment"] = alignment
        return res
