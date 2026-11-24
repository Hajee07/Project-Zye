"""
Metadata Extraction Engine for Microsoft Excel Workbooks & Worksheets — Zye Day 22.
Runs exclusively on the STA worker thread to extract structured metadata safely.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional
from zye_office.models.excel_models import (
    ExcelWorkbookMetadata,
    ExcelWorksheetMetadata,
    ExcelCellMetadata,
)

logger = logging.getLogger("zye.office.excel.metadata")


class ExcelMetadataExtractor:
    """Extracts typed metadata from Excel COM dispatch objects."""

    @staticmethod
    def extract_workbook_metadata(app: Any, wb: Any) -> ExcelWorkbookMetadata:
        """Extract comprehensive workbook metadata."""
        if wb is None:
            return ExcelWorkbookMetadata(
                status="NO_ACTIVE_WORKBOOK",
                message="No active workbook is currently open.",
            )

        name = getattr(wb, "Name", "Untitled.xlsx")
        try:
            full_path = getattr(wb, "FullName", None)
        except Exception:
            full_path = None

        saved = getattr(wb, "Saved", True)
        read_only = getattr(wb, "ReadOnly", False)
        protected = getattr(wb, "ProtectStructure", False)

        file_size = None
        ext = None
        if full_path and os.path.exists(full_path):
            try:
                file_size = os.path.getsize(full_path)
                ext = os.path.splitext(full_path)[1]
            except Exception:
                pass

        sheet_names: List[str] = []
        try:
            for s in wb.Worksheets:
                sheet_names.append(s.Name)
        except Exception:
            pass

        active_sheet_name = None
        active_ws = getattr(app, "ActiveSheet", None)
        if active_ws:
            try:
                active_sheet_name = active_ws.Name
            except Exception:
                pass

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

        used_rows = 0
        used_cols = 0
        if active_ws:
            try:
                used_rows = active_ws.UsedRange.Rows.Count
                used_cols = active_ws.UsedRange.Columns.Count
            except Exception:
                pass

        calc_mode = "Automatic"
        try:
            # -4135 is manual, -4105 is automatic
            c_val = getattr(app, "Calculation", None)
            if c_val == -4135:
                calc_mode = "Manual"
            elif c_val == 2:
                calc_mode = "Semiautomatic"
        except Exception:
            pass

        table_count = 0
        pivot_count = 0
        chart_count = 0
        try:
            for s in wb.Worksheets:
                table_count += getattr(s.ListObjects, "Count", 0)
                pivot_count += getattr(s.PivotTables(), "Count", 0)
                chart_count += getattr(s.ChartObjects(), "Count", 0)
        except Exception:
            pass

        return ExcelWorkbookMetadata(
            status="SUCCESS",
            workbook_name=name,
            filename=name,
            path=full_path,
            file_extension=ext,
            sheet_count=len(sheet_names),
            sheet_names=sheet_names,
            active_sheet_name=active_sheet_name,
            is_saved=saved,
            is_read_only=read_only,
            is_protected=protected,
            file_size_bytes=file_size,
            calculation_mode=calc_mode,
            table_count=table_count,
            pivot_count=pivot_count,
            chart_count=chart_count,
            active_cell=active_cell,
            selected_range=selected_range,
            used_rows=used_rows,
            used_columns=used_cols,
        )

    @staticmethod
    def extract_worksheet_metadata(ws: Any) -> ExcelWorksheetMetadata:
        """Extract worksheet metadata."""
        name = getattr(ws, "Name", "")
        idx = getattr(ws, "Index", 1)
        visible = getattr(ws, "Visible", True) == -1  # xlSheetVisible = -1
        protected = getattr(ws, "ProtectContents", False)

        used_addr = "A1"
        row_count = 0
        col_count = 0
        try:
            ur = ws.UsedRange
            used_addr = ur.Address
            row_count = ur.Rows.Count
            col_count = ur.Columns.Count
        except Exception:
            pass

        tab_color = None
        try:
            tab_color = getattr(ws.Tab, "Color", None)
        except Exception:
            pass

        table_count = getattr(ws.ListObjects, "Count", 0)
        chart_count = getattr(ws.ChartObjects(), "Count", 0)
        pivot_count = getattr(ws.PivotTables(), "Count", 0)

        return ExcelWorksheetMetadata(
            status="SUCCESS",
            sheet_name=name,
            index=idx,
            is_visible=visible,
            is_protected=protected,
            used_range_address=used_addr,
            row_count=row_count,
            column_count=col_count,
            tab_color=tab_color,
            tables_count=table_count,
            charts_count=chart_count,
            pivot_tables_count=pivot_count,
        )
