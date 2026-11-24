"""
Input & Document Identity Validator for Microsoft Word Automation — Zye Day 21.
Validates table dimensions, formatting bounds, Unicode preservation, and prevents identity mismatches.
"""

from __future__ import annotations

import pathlib
from typing import Any, Optional

from zye_office.path_validator import OfficePathValidator
from zye_office.word.word_errors import (
    WordDocumentIdentityMismatchError,
    WordFormattingError,
    WordTableSizeExceededError,
    WordValidationError,
)

MAX_TABLE_ROWS = 500
MAX_TABLE_COLUMNS = 50
MAX_CELLS_PER_OPERATION = 10000


class WordValidator:
    """Validates parameters, formatting ranges, and active document identity."""

    def __init__(self, path_validator: Optional[OfficePathValidator] = None) -> None:
        self.path_validator = path_validator or OfficePathValidator()

    @classmethod
    def validate_table_dimensions(cls, rows: int, columns: int) -> None:
        if rows <= 0 or columns <= 0:
            raise WordValidationError("Table rows and columns must be strictly positive integers.")
        if rows > MAX_TABLE_ROWS or columns > MAX_TABLE_COLUMNS:
            raise WordTableSizeExceededError(
                f"Requested table dimensions ({rows}x{columns}) exceed safety limits "
                f"(max {MAX_TABLE_ROWS} rows, {MAX_TABLE_COLUMNS} columns)."
            )
        if rows * columns > MAX_CELLS_PER_OPERATION:
            raise WordTableSizeExceededError(
                f"Total table cells ({rows * columns}) exceed maximum batch limit of {MAX_CELLS_PER_OPERATION} cells."
            )

    @classmethod
    def validate_table_bounds(cls, rows: int, columns: int) -> None:
        cls.validate_table_dimensions(rows, columns)

    @classmethod
    def validate_font_size(cls, size: Optional[float]) -> None:
        if size is not None:
            if size < 1.0 or size > 1638.0:
                raise WordFormattingError(f"Font size {size}pt is out of valid Word bounds (1.0 to 1638.0 pt).")

    @classmethod
    def validate_line_spacing(cls, spacing: Optional[float]) -> None:
        if spacing is not None and (spacing < 0.5 or spacing > 10.0):
            raise WordFormattingError(f"Line spacing {spacing} is out of bounds (0.5 to 10.0).")

    def validate_alignment(self, align_str: Optional[str]) -> Optional[int]:
        if not align_str:
            return None
        norm = align_str.strip().lower()
        mapping = {
            "left": 0,
            "center": 1,
            "right": 2,
            "justify": 3,
            "justified": 3,
        }
        if norm not in mapping:
            raise WordFormattingError(f"Alignment '{align_str}' is invalid. Allowed: left, center, right, justify.")
        return mapping[norm]

    def validate_document_identity(self, expected_name: Optional[str], active_doc: Any) -> None:
        """Ensures the currently active document matches the expected target to avoid editing the wrong file."""
        if not expected_name:
            return
        if active_doc is None:
            raise WordDocumentIdentityMismatchError("No active document open to verify identity against.")

        actual_name = getattr(active_doc, "Name", "")
        if actual_name.lower().strip() != expected_name.lower().strip():
            raise WordDocumentIdentityMismatchError(
                f"Document identity mismatch! Expected '{expected_name}', but active document is '{actual_name}'. "
                f"Aborting write operation to prevent editing an unintended document."
            )

    def validate_unicode_text(self, text: str) -> str:
        """Verifies text string is clean Unicode without corrupting Tamil or multi-byte glyphs."""
        if not isinstance(text, str):
            text = str(text)
        # Ensure roundtrip encode/decode to utf-8 preserves identical string
        encoded = text.encode("utf-8")
        decoded = encoded.decode("utf-8")
        if decoded != text:
            raise WordValidationError("Unicode encoding mismatch detected in input text.")
        return text
