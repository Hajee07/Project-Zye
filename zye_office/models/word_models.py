"""
Data Models & Pydantic Schemas for Microsoft Word Automation — Zye Day 21.
"""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class WordDocumentMetadata(BaseModel):
    status: str = "SUCCESS"
    app_name: str = "word"
    document_name: str = ""
    title: Optional[str] = None
    path: Optional[str] = None
    is_saved: bool = True
    is_read_only: bool = False
    is_protected: bool = False
    word_count: int = 0
    page_count: int = 0
    character_count: int = 0
    paragraph_count: int = 0
    paragraphs_count: Optional[int] = None
    table_count: int = 0
    section_count: int = 0
    revision_count: int = 0
    comment_count: int = 0
    track_changes_active: bool = False
    preview_text: Optional[str] = None
    message: Optional[str] = None


class WordFormatOptions(BaseModel):
    font_name: Optional[str] = None
    font_size: Optional[float] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None
    color: Optional[int] = None
    highlight: Optional[int] = None
    strikethrough: Optional[bool] = None
    subscript: Optional[bool] = None
    superscript: Optional[bool] = None
    alignment: Optional[str] = None  # left, center, right, justify
    line_spacing: Optional[float] = None
    space_before: Optional[float] = None
    space_after: Optional[float] = None
    first_line_indent: Optional[float] = None
    left_indent: Optional[float] = None
    right_indent: Optional[float] = None


class WordTableConfig(BaseModel):
    rows: int = 1
    columns: int = 1
    table_id: Optional[int] = None
    style_name: Optional[str] = None
    autofit: Optional[str] = "window"  # fixed, content, window
    repeat_header: Optional[bool] = True
    data: Optional[List[List[Any]]] = None


class WordPageLayoutConfig(BaseModel):
    orientation: Optional[str] = "PORTRAIT"  # PORTRAIT, LANDSCAPE
    paper_size: Optional[str] = "A4"  # A4, A3, LETTER, LEGAL, CUSTOM
    top_margin_pt: Optional[float] = None
    bottom_margin_pt: Optional[float] = None
    left_margin_pt: Optional[float] = None
    right_margin_pt: Optional[float] = None
    columns: Optional[int] = 1
    column_spacing_pt: Optional[float] = None


class WordHeaderFooterConfig(BaseModel):
    header_text: Optional[str] = None
    footer_text: Optional[str] = None
    first_page_different: Optional[bool] = False
    first_page_header: Optional[str] = None
    first_page_footer: Optional[str] = None
    include_page_numbers: Optional[bool] = True
    page_number_position: Optional[str] = "footer_right"


class WordRevisionItem(BaseModel):
    index: int
    author: str = ""
    date: Optional[str] = None
    revision_type: str = "unknown"
    text_snippet: str = ""


class WordCommentItem(BaseModel):
    index: int
    author: str = ""
    date: Optional[str] = None
    text: str = ""
    resolved: bool = False
    scope_text: str = ""


class WordMailMergeConfig(BaseModel):
    source_path: str
    output_dir: Optional[str] = None
    preview_record: int = 1


class WordAccessibilityIssue(BaseModel):
    category: str
    severity: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    description: str
    target_element: str
    suggested_fix: str


class WordAccessibilityReport(BaseModel):
    status: str = "SUCCESS"
    document_name: str
    total_issues: int
    compliance_score: int = 100
    passed: bool = True
    issues: List[WordAccessibilityIssue] = Field(default_factory=list)
    is_compliant: bool = True
