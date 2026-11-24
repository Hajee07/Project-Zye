"""
Entity Provenance Formatter.
Constructs traceable citation markers (e.g., "[Report.pdf, Page 3]",
"[Data.xlsx, Sheet 'Finance']", "[main.py, Line 120]").
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from zye_computer_intelligence.schemas.entity_schemas import EntityMention


def format_provenance_citation(mention: EntityMention) -> str:
    """Creates a human-readable citation string from an EntityMention."""
    file_name = Path(mention.file_path).name

    parts = [file_name]
    if mention.page_number is not None:
        parts.append(f"Page {mention.page_number}")
    if mention.sheet_name is not None:
        parts.append(f"Sheet '{mention.sheet_name}'")
    if mention.section_name is not None:
        parts.append(f"Section '{mention.section_name}'")
    if mention.line_number is not None:
        parts.append(f"Line {mention.line_number}")

    return f"[{', '.join(parts)}]"


def build_provenance_dict(
    file_path: str,
    page_number: Optional[int] = None,
    sheet_name: Optional[str] = None,
    section_name: Optional[str] = None,
    line_number: Optional[int] = None,
    char_start: Optional[int] = None,
    char_end: Optional[int] = None,
) -> dict:
    """Builds a structured provenance dictionary for indexing."""
    return {
        "file_name": Path(file_path).name,
        "file_path": file_path,
        "page_number": page_number,
        "sheet_name": sheet_name,
        "section_name": section_name,
        "line_number": line_number,
        "char_start": char_start,
        "char_end": char_end,
    }
