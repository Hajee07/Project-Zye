"""
Live Office State Inspection Engine — Zye Day 20.
Inspects active documents, workbooks, presentations, and Outlook sessions via COM
inside the STA worker thread, extracting bounded metadata without leaking private content.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from zye_office.com_runtime import OfficeCOMRuntime
from zye_office.com_worker import run_on_sta_worker
from zye_office.errors import format_office_error
from zye_office.models import (
    ExcelWorkbookMetadata,
    OutlookSessionMetadata,
    PowerPointPresentationMetadata,
    WordDocumentMetadata,
)

logger = logging.getLogger("zye.office.state_inspector")

DEFAULT_WORD_PREVIEW_LIMIT = 1500
DEFAULT_EXCEL_MAX_ROWS = 100
DEFAULT_EXCEL_MAX_COLS = 30


class OfficeStateInspector:
    """
    Extracts structural metadata and bounded summaries from live, open Microsoft Office applications.
    """

    def __init__(self, com_runtime: Optional[OfficeCOMRuntime] = None) -> None:
        self.com_runtime = com_runtime or OfficeCOMRuntime()

    # =========================================================================
    # Microsoft Word Inspection
    # =========================================================================

    def inspect_word_state(self, preview_limit: int = DEFAULT_WORD_PREVIEW_LIMIT) -> dict[str, Any]:
        """
        Inspect the active Word instance and document.
        Returns filename, page count, word count, paragraph count, and bounded preview.
        """
        def _sta_inspect_word() -> dict[str, Any]:
            app = self.com_runtime.get_raw_com_object("word")
            if app is None:
                # Attempt to attach
                conn = self.com_runtime.connect_office_application("word")
                if conn.get("status") != "SUCCESS":
                    return conn
                app = self.com_runtime.get_raw_com_object("word")

            if app is None:
                return format_office_error("WORD_NOT_RUNNING", "Word is not running or accessible.", app_name="word")

            try:
                # Check Documents count
                doc_count = getattr(app.Documents, "Count", 0)
                if doc_count == 0:
                    return WordDocumentMetadata(
                        status="NO_ACTIVE_DOCUMENT",
                        app_name="word",
                        message="Word is running, but no active document is currently open.",
                    ).model_dump()

                doc = app.ActiveDocument
                if doc is None:
                    return WordDocumentMetadata(
                        status="NO_ACTIVE_DOCUMENT",
                        app_name="word",
                        message="Word is running, but no active document is currently focused.",
                    ).model_dump()

                name = getattr(doc, "Name", "Untitled.docx")
                try:
                    path = getattr(doc, "FullName", None)
                except Exception:
                    path = None

                saved = getattr(doc, "Saved", True)
                read_only = getattr(doc, "ReadOnly", False)
                track_changes = getattr(doc, "TrackRevisions", False)

                # Compute counts
                word_count = 0
                char_count = 0
                para_count = 0
                section_count = 0
                page_count = 1

                try:
                    word_count = doc.Words.Count
                except Exception:
                    pass
                try:
                    char_count = doc.Characters.Count
                except Exception:
                    pass
                try:
                    para_count = doc.Paragraphs.Count
                except Exception:
                    pass
                try:
                    section_count = doc.Sections.Count
                except Exception:
                    pass
                try:
                    # wdStatisticPages = 2
                    page_count = doc.ComputeStatistics(2)
                except Exception:
                    pass

                # Bounded text preview
                preview = ""
                try:
                    raw_text = doc.Range(0, min(char_count, preview_limit)).Text
                    preview = (raw_text or "").strip()
                except Exception:
                    pass

                meta = WordDocumentMetadata(
                    status="SUCCESS",
                    app_name="word",
                    filename=name,
                    path=path,
                    is_saved=saved,
                    is_read_only=read_only,
                    page_count=page_count,
                    word_count=word_count,
                    character_count=char_count,
                    paragraph_count=para_count,
                    section_count=section_count,
                    track_changes_active=track_changes,
                    preview_text=preview[:preview_limit],
                )
                return meta.model_dump()
            except Exception as exc:
                return format_office_error(
                    "WORD_INSPECTION_FAILED",
                    f"Failed to inspect active Word document: {exc}",
                    app_name="word",
                )

        return self.com_runtime.worker.run(_sta_inspect_word)

    # =========================================================================
    # Microsoft Excel Inspection
    # =========================================================================

    def inspect_excel_state(self) -> dict[str, Any]:
        """
        Inspect active Excel instance, workbook, and worksheet.
        Returns workbook name, sheet names, active cell, used range dimensions, and calculation mode.
        """
        def _sta_inspect_excel() -> dict[str, Any]:
            app = self.com_runtime.get_raw_com_object("excel")
            if app is None:
                conn = self.com_runtime.connect_office_application("excel")
                if conn.get("status") != "SUCCESS":
                    return conn
                app = self.com_runtime.get_raw_com_object("excel")

            if app is None:
                return format_office_error("EXCEL_NOT_RUNNING", "Excel is not running or accessible.", app_name="excel")

            try:
                wb_count = getattr(app.Workbooks, "Count", 0)
                if wb_count == 0:
                    return ExcelWorkbookMetadata(
                        status="NO_ACTIVE_WORKBOOK",
                        app_name="excel",
                        message="Excel is running, but no active workbook is currently open.",
                    ).model_dump()

                wb = app.ActiveWorkbook
                if wb is None:
                    return ExcelWorkbookMetadata(
                        status="NO_ACTIVE_WORKBOOK",
                        app_name="excel",
                        message="Excel is running, but no workbook is focused.",
                    ).model_dump()

                wb_name = getattr(wb, "Name", "Untitled.xlsx")
                try:
                    wb_path = getattr(wb, "FullName", None)
                except Exception:
                    wb_path = None

                saved = getattr(wb, "Saved", True)
                read_only = getattr(wb, "ReadOnly", False)

                # Worksheets
                sheet_names = []
                try:
                    for s in wb.Worksheets:
                        sheet_names.append(s.Name)
                except Exception:
                    pass

                ws = getattr(app, "ActiveSheet", None)
                active_sheet_name = getattr(ws, "Name", None) if ws else None

                # Active cell and selection
                active_cell = None
                selected_range = None
                try:
                    active_cell = getattr(app.ActiveCell, "Address", None)
                except Exception:
                    pass
                try:
                    selected_range = getattr(app.Selection, "Address", None)
                except Exception:
                    pass

                # UsedRange bounded dimensions
                used_rows = 0
                used_cols = 0
                if ws:
                    try:
                        used_rows = ws.UsedRange.Rows.Count
                        used_cols = ws.UsedRange.Columns.Count
                    except Exception:
                        pass

                calc_mode = "Automatic"
                try:
                    # xlCalculationManual = -4135, xlCalculationAutomatic = -4105
                    calc_val = getattr(app, "Calculation", None)
                    if calc_val == -4135:
                        calc_mode = "Manual"
                except Exception:
                    pass

                meta = ExcelWorkbookMetadata(
                    status="SUCCESS",
                    app_name="excel",
                    filename=wb_name,
                    path=wb_path,
                    is_saved=saved,
                    is_read_only=read_only,
                    active_sheet_name=active_sheet_name,
                    sheet_names=sheet_names,
                    active_cell=active_cell,
                    selected_range=selected_range,
                    used_rows=used_rows,
                    used_columns=used_cols,
                    calculation_mode=calc_mode,
                )
                return meta.model_dump()
            except Exception as exc:
                return format_office_error(
                    "EXCEL_INSPECTION_FAILED",
                    f"Failed to inspect active Excel workbook: {exc}",
                    app_name="excel",
                )

        return self.com_runtime.worker.run(_sta_inspect_excel)

    # =========================================================================
    # Microsoft PowerPoint Inspection
    # =========================================================================

    def inspect_powerpoint_state(self) -> dict[str, Any]:
        """
        Inspect active PowerPoint instance and presentation.
        Returns presentation name, slide count, active slide index, and slide titles.
        """
        def _sta_inspect_powerpoint() -> dict[str, Any]:
            app = self.com_runtime.get_raw_com_object("powerpoint")
            if app is None:
                conn = self.com_runtime.connect_office_application("powerpoint")
                if conn.get("status") != "SUCCESS":
                    return conn
                app = self.com_runtime.get_raw_com_object("powerpoint")

            if app is None:
                return format_office_error("POWERPOINT_NOT_RUNNING", "PowerPoint is not running or accessible.", app_name="powerpoint")

            try:
                pres_count = getattr(app.Presentations, "Count", 0)
                if pres_count == 0:
                    return PowerPointPresentationMetadata(
                        status="NO_ACTIVE_PRESENTATION",
                        app_name="powerpoint",
                        message="PowerPoint is running, but no active presentation is currently open.",
                    ).model_dump()

                pres = getattr(app, "ActivePresentation", None)
                if pres is None:
                    return PowerPointPresentationMetadata(
                        status="NO_ACTIVE_PRESENTATION",
                        app_name="powerpoint",
                        message="PowerPoint is running, but no presentation is focused.",
                    ).model_dump()

                pres_name = getattr(pres, "Name", "Untitled.pptx")
                try:
                    pres_path = getattr(pres, "FullName", None)
                except Exception:
                    pres_path = None

                saved = getattr(pres, "Saved", True)
                read_only = getattr(pres, "ReadOnly", False)
                slide_count = pres.Slides.Count

                active_idx = 1
                try:
                    active_idx = app.ActiveWindow.View.Slide.SlideIndex
                except Exception:
                    pass

                # Extract slide titles (bounded)
                titles: list[str] = []
                for i in range(1, min(slide_count + 1, 50)):
                    try:
                        s = pres.Slides(i)
                        s_title = ""
                        if hasattr(s.Shapes, "HasTitle") and s.Shapes.HasTitle:
                            s_title = s.Shapes.Title.TextFrame.TextRange.Text.strip()
                        titles.append(s_title or f"Slide {i}")
                    except Exception:
                        titles.append(f"Slide {i}")

                # Slide dimensions
                slide_w = getattr(pres.PageSetup, "SlideWidth", 0.0)
                slide_h = getattr(pres.PageSetup, "SlideHeight", 0.0)

                meta = PowerPointPresentationMetadata(
                    status="SUCCESS",
                    app_name="powerpoint",
                    filename=pres_name,
                    path=pres_path,
                    is_saved=saved,
                    is_read_only=read_only,
                    slide_count=slide_count,
                    active_slide_index=active_idx,
                    slide_titles=titles,
                    slide_width=float(slide_w),
                    slide_height=float(slide_h),
                )
                return meta.model_dump()
            except Exception as exc:
                return format_office_error(
                    "POWERPOINT_INSPECTION_FAILED",
                    f"Failed to inspect active PowerPoint presentation: {exc}",
                    app_name="powerpoint",
                )

        return self.com_runtime.worker.run(_sta_inspect_powerpoint)

    # =========================================================================
    # Microsoft Outlook Inspection
    # =========================================================================

    def inspect_outlook_state(self) -> dict[str, Any]:
        """
        Inspect Outlook COM application availability, session state, and active folder metadata.
        Does NOT read private email message bodies or personal contact lists.
        """
        def _sta_inspect_outlook() -> dict[str, Any]:
            app = self.com_runtime.get_raw_com_object("outlook")
            if app is None:
                conn = self.com_runtime.connect_office_application("outlook")
                if conn.get("status") != "SUCCESS":
                    return conn
                app = self.com_runtime.get_raw_com_object("outlook")

            if app is None:
                return format_office_error("OUTLOOK_NOT_RUNNING", "Outlook is not running or accessible.", app_name="outlook")

            try:
                ver = str(getattr(app, "Version", ""))
                explorers_count = getattr(app.Explorers, "Count", 0)
                inspectors_count = getattr(app.Inspectors, "Count", 0)

                folder_name = None
                try:
                    active_expl = app.ActiveExplorer()
                    if active_expl:
                        folder_name = active_expl.CurrentFolder.Name
                except Exception:
                    pass

                profile_name = None
                try:
                    profile_name = app.Session.CurrentProfileName
                except Exception:
                    pass

                meta = OutlookSessionMetadata(
                    status="SUCCESS",
                    app_name="outlook",
                    application_version=ver,
                    is_connected=True,
                    current_folder_name=folder_name,
                    explorer_count=explorers_count,
                    inspector_count=inspectors_count,
                    profile_name=profile_name,
                )
                return meta.model_dump()
            except Exception as exc:
                return format_office_error(
                    "OUTLOOK_INSPECTION_FAILED",
                    f"Failed to inspect Outlook COM session: {exc}",
                    app_name="outlook",
                )

        return self.com_runtime.worker.run(_sta_inspect_outlook)

    def inspect_live_office_app(self, app_name: str) -> dict[str, Any]:
        """Dispatch to appropriate application state inspector by name."""
        norm = (app_name or "").strip().lower()
        if norm in ("word", "winword", "doc", "docx"):
            return self.inspect_word_state()
        elif norm in ("excel", "sheet", "xlsx", "xls"):
            return self.inspect_excel_state()
        elif norm in ("powerpoint", "ppt", "pptx", "presentation"):
            return self.inspect_powerpoint_state()
        elif norm in ("outlook", "mail", "email"):
            return self.inspect_outlook_state()
        else:
            return format_office_error(
                "UNSUPPORTED_OFFICE_APP",
                f"Unsupported Office application '{app_name}'. Supported: word, excel, powerpoint, outlook.",
                app_name=app_name,
            )

    def inspect_active_word_document(self, preview_limit: int = DEFAULT_WORD_PREVIEW_LIMIT) -> dict[str, Any]:
        """Convenience alias for inspect_word_state."""
        return self.inspect_word_state(preview_limit=preview_limit)

    def inspect_active_excel_workbook(self) -> dict[str, Any]:
        """Convenience alias for inspect_excel_state."""
        return self.inspect_excel_state()

    def inspect_active_powerpoint_presentation(self) -> dict[str, Any]:
        """Convenience alias for inspect_powerpoint_state."""
        return self.inspect_powerpoint_state()

    def inspect_active_outlook_session(self) -> dict[str, Any]:
        """Convenience alias for inspect_outlook_state."""
        return self.inspect_outlook_state()
