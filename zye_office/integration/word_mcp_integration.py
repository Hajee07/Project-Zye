"""
Word MCP Tool Integration Facade — Zye Day 21.
Encapsulates all modular Word engines and coordinates validation, permissions, and execution.
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any, Dict, List, Optional

from zye_office.models.word_models import WordFormatOptions
from zye_office.word import (
    WordAdapter,
    WordDocumentManager,
    WordContentEngine,
    WordFormattingEngine,
    WordStyleManager,
    WordTableEngine,
    WordHeaderFooterEngine,
    WordSectionManager,
    WordPageLayoutEngine,
    WordListEngine,
    WordTOCEngine,
    WordHyperlinkEngine,
    WordBookmarkEngine,
    WordTrackChangesEngine,
    WordReviewEngine,
    WordCommentEngine,
    WordMailMergeEngine,
    WordMetadataEngine,
    WordAccessibilityEngine,
    WordPermissionEngine,
    WordValidator,
    format_word_error,
)
from zye_office.file_exporter import OfficeFileExporter

logger = logging.getLogger("zye.office.word.mcp_facade")


class WordMCPIntegrationFacade:
    """Consolidated facade managing all Word automation capabilities."""

    def __init__(self) -> None:
        self.adapter = WordAdapter()
        self.validator = WordValidator()
        self.doc_mgr = WordDocumentManager(adapter=self.adapter)
        self.content_engine = WordContentEngine(adapter=self.adapter, validator=self.validator)
        self.formatting_engine = WordFormattingEngine(adapter=self.adapter, validator=self.validator)
        self.style_mgr = WordStyleManager(adapter=self.adapter)
        self.table_engine = WordTableEngine(adapter=self.adapter, validator=self.validator)
        self.header_footer = WordHeaderFooterEngine(adapter=self.adapter, validator=self.validator)
        self.section_mgr = WordSectionManager(adapter=self.adapter)
        self.layout_engine = WordPageLayoutEngine(adapter=self.adapter)
        self.list_engine = WordListEngine(adapter=self.adapter, validator=self.validator)
        self.toc_engine = WordTOCEngine(adapter=self.adapter)
        self.hyperlink_engine = WordHyperlinkEngine(adapter=self.adapter, validator=self.validator)
        self.bookmark_engine = WordBookmarkEngine(adapter=self.adapter)
        self.track_changes_engine = WordTrackChangesEngine(adapter=self.adapter)
        self.review_engine = WordReviewEngine(adapter=self.adapter)
        self.comment_engine = WordCommentEngine(adapter=self.adapter, validator=self.validator)
        self.mail_merge_engine = WordMailMergeEngine(adapter=self.adapter, validator=self.validator)
        self.metadata_engine = WordMetadataEngine(adapter=self.adapter, validator=self.validator)
        self.accessibility_engine = WordAccessibilityEngine(adapter=self.adapter)
        self.file_exporter = OfficeFileExporter(
            runtime=self.adapter.com_runtime,
            session_manager=None,  # Handled on doc level
            path_validator=self.validator.path_validator,
        )
        self.capabilities_config = {}
        config_path = pathlib.Path(__file__).resolve().parent.parent.parent / "configs" / "word_capabilities.toml"
        if config_path.exists():
            try:
                import tomllib
                with open(config_path, "rb") as f:
                    self.capabilities_config = tomllib.load(f)
            except Exception:
                pass

    # Document Lifecycle
    def create_document(self) -> Dict[str, Any]:
        return self.doc_mgr.create_word_document()

    def open_document(self, file_path: str, read_only: bool = False) -> Dict[str, Any]:
        return self.doc_mgr.open_word_document(file_path, read_only=read_only)

    def save_document(self, path: Optional[str] = None) -> Dict[str, Any]:
        return self.doc_mgr.save_word_document(path=path)

    def save_document_as(self, file_path: str) -> Dict[str, Any]:
        return self.doc_mgr.save_word_document_as(file_path)

    def close_document(self, save_changes: bool = False) -> Dict[str, Any]:
        return self.doc_mgr.close_word_document(save_changes=save_changes)

    def inspect_document(self, max_preview_chars: int = 1500) -> Dict[str, Any]:
        return self.doc_mgr.get_document_metadata(max_preview_chars=max_preview_chars)

    # Content
    def insert_text(self, text: str, location: str = "end") -> Dict[str, Any]:
        return self.content_engine.insert_text(text, location=location)

    def replace_text(self, old_text: str, new_text: str, replace_all: bool = False, confirmed: bool = False) -> Dict[str, Any]:
        if replace_all:
            WordPermissionEngine.enforce_gate("word.replace_text", confirmed=confirmed)
        return self.content_engine.replace_exact_text(old_text, new_text, replace_all=replace_all)

    def delete_selected_text(self, confirmed: bool = False) -> Dict[str, Any]:
        WordPermissionEngine.enforce_gate("word.delete_selected_text", confirmed=confirmed)
        return self.content_engine.delete_selected_text()

    def insert_page_break(self) -> Dict[str, Any]:
        return self.content_engine.insert_page_break()

    def insert_section_break(self) -> Dict[str, Any]:
        return self.content_engine.insert_section_break()

    # Formatting & Styles
    def format_text(self, format_options: Dict[str, Any]) -> Dict[str, Any]:
        opts = WordFormatOptions(**format_options)
        return self.formatting_engine.apply_formatting(opts)

    def apply_style(self, style_name: str) -> Dict[str, Any]:
        return self.style_mgr.apply_word_style(style_name)

    def apply_preset(self, preset_name: str) -> Dict[str, Any]:
        return self.style_mgr.apply_style_preset(preset_name)

    # Tables
    def create_table(self, rows: int, columns: int, autofit: str = "window", data: Optional[List[List[Any]]] = None, style_preset: Optional[str] = None) -> Dict[str, Any]:
        return self.table_engine.create_word_table(rows, columns, autofit=autofit, data=data, style_preset=style_preset)

    def populate_table(self, table_id: int, data: List[List[Any]]) -> Dict[str, Any]:
        return self.table_engine.populate_word_table(table_id, data)

    def add_table_row(self, table_id: int) -> Dict[str, Any]:
        return self.table_engine.add_table_row(table_id)

    def delete_table_row(self, table_id: int, row_index: int) -> Dict[str, Any]:
        return self.table_engine.delete_table_row(table_id, row_index)

    # Headers & Footers
    def set_header(self, text: str, section_index: int = 1, alignment: str = "center") -> Dict[str, Any]:
        return self.header_footer.set_document_header(text, section_index=section_index, alignment=alignment)

    def set_footer(self, text: str, section_index: int = 1, alignment: str = "center") -> Dict[str, Any]:
        return self.header_footer.set_document_footer(text, section_index=section_index, alignment=alignment)

    def insert_page_numbers(self, position: str = "footer_right", section_index: int = 1) -> Dict[str, Any]:
        return self.header_footer.insert_page_numbers(position=position, section_index=section_index)

    def set_first_page_header(self, text: str, section_index: int = 1) -> Dict[str, Any]:
        return self.header_footer.set_different_first_page(enabled=True, section_index=section_index, first_page_header_text=text)

    # Layout
    def set_page_orientation(self, orientation: str, section_index: Optional[int] = None) -> Dict[str, Any]:
        return self.layout_engine.set_page_orientation(orientation, section_index=section_index)

    def set_paper_size(self, size: str, section_index: Optional[int] = None) -> Dict[str, Any]:
        return self.layout_engine.set_paper_size(size, section_index=section_index)

    def set_page_margins(self, top: Optional[float] = None, bottom: Optional[float] = None, left: Optional[float] = None, right: Optional[float] = None, section_index: Optional[int] = None) -> Dict[str, Any]:
        return self.layout_engine.set_page_margins(top_pt=top, bottom_pt=bottom, left_pt=left, right_pt=right, section_index=section_index)

    # Lists
    def create_bullet_list(self, items: List[str]) -> Dict[str, Any]:
        return self.list_engine.create_bullet_list(items)

    def create_numbered_list(self, items: List[str]) -> Dict[str, Any]:
        return self.list_engine.create_numbered_list(items)

    # Table of Contents
    def insert_toc(self, upper_level: int = 1, lower_level: int = 3) -> Dict[str, Any]:
        return self.toc_engine.insert_table_of_contents(upper_level=upper_level, lower_level=lower_level)

    def update_toc(self) -> Dict[str, Any]:
        return self.toc_engine.update_table_of_contents()

    # Hyperlinks & Bookmarks
    def insert_hyperlink(self, display_text: str, url: str) -> Dict[str, Any]:
        return self.hyperlink_engine.insert_hyperlink(display_text, url)

    def create_bookmark(self, name: str) -> Dict[str, Any]:
        return self.bookmark_engine.create_bookmark(name)

    # Track Changes & Review
    def get_track_changes_status(self) -> Dict[str, Any]:
        return self.track_changes_engine.get_track_changes_status()

    def set_track_changes(self, enabled: bool) -> Dict[str, Any]:
        return self.track_changes_engine.set_track_changes(enabled)

    def get_revisions(self) -> Dict[str, Any]:
        return self.track_changes_engine.get_document_revisions()

    def accept_revision(self, revision_id: int) -> Dict[str, Any]:
        return self.track_changes_engine.accept_revision(revision_id)

    def reject_revision(self, revision_id: int) -> Dict[str, Any]:
        return self.track_changes_engine.reject_revision(revision_id)

    def accept_all_revisions(self, confirmed: bool = False) -> Dict[str, Any]:
        return self.track_changes_engine.accept_all_revisions(confirmed=confirmed)

    def reject_all_revisions(self, confirmed: bool = False) -> Dict[str, Any]:
        return self.track_changes_engine.reject_all_revisions(confirmed=confirmed)

    # Comments
    def add_comment(self, text: str) -> Dict[str, Any]:
        return self.comment_engine.add_comment(text)

    def get_comments(self) -> Dict[str, Any]:
        return self.comment_engine.get_document_comments()

    def resolve_comment(self, comment_id: int) -> Dict[str, Any]:
        return self.comment_engine.resolve_comment(comment_id)

    # Mail Merge
    def inspect_mail_merge(self) -> Dict[str, Any]:
        return self.mail_merge_engine.inspect_mail_merge_settings()

    def connect_merge_source(self, source_path: str) -> Dict[str, Any]:
        return self.mail_merge_engine.connect_mail_merge_source(source_path)

    def execute_mail_merge(self, confirmed: bool = False) -> Dict[str, Any]:
        WordPermissionEngine.enforce_gate("word.execute_mail_merge", confirmed=confirmed)
        return self.mail_merge_engine.execute_mail_merge(confirmed=confirmed)

    # Metadata & Statistics
    def get_statistics(self) -> Dict[str, Any]:
        return self.metadata_engine.get_document_statistics()

    def set_document_properties(self, properties: Dict[str, str]) -> Dict[str, Any]:
        return self.metadata_engine.set_document_properties(properties)

    # Accessibility
    def inspect_accessibility(self) -> Dict[str, Any]:
        return self.accessibility_engine.inspect_document_accessibility()

    # Advanced PDF Export
    def export_pdf_advanced(self, output_path: str, overwrite: bool = False) -> Dict[str, Any]:
        def _sta_export() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            canonical_out = self.validator.path_validator.validate_path(output_path, allowed_extensions=[".pdf"])
            import pathlib
            if self.validator.path_validator.validate_overwrite(pathlib.Path(canonical_out), confirmed=overwrite).get("status") == "CONFIRMATION_REQUIRED":
                return {
                    "status": "CONFIRMATION_REQUIRED",
                    "message": f"PDF file '{canonical_out}' already exists. Pass overwrite=True to confirm overwrite.",
                }

            # ExportAsFixedFormat
            doc.ExportAsFixedFormat(
                OutputFileName=canonical_out,
                ExportFormat=17,  # wdExportFormatPDF
                OpenAfterExport=False,
                OptimizeFor=0,
            )

            import os
            size = os.path.getsize(canonical_out)
            return {
                "status": "SUCCESS",
                "output_path": canonical_out,
                "file_size_bytes": size,
                "verified": size > 0,
                "message": f"PDF exported successfully ({size} bytes).",
            }

        return self.adapter.worker.run(_sta_export)
