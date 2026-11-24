"""
Worksheet Management Engine for Microsoft Excel — Zye Day 22.
Handles sheet creation, renaming, deletion, freezing panes, and tab colors.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.excel.excel_adapter import ExcelAdapter
from zye_office.excel.excel_errors import (
    ExcelNoActiveWorkbookError,
    ExcelSecurityError,
    ExcelSheetNotFoundError,
    ExcelSheetProtectedError,
)
from zye_office.excel.excel_metadata import ExcelMetadataExtractor
from zye_office.excel.excel_permissions import ExcelPermissionEngine
from zye_office.excel.excel_validator import ExcelValidator

logger = logging.getLogger("zye.office.excel.worksheet")


class ExcelWorksheetManager:
    """Manages worksheet lifecycles inside the active workbook."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        validator: Optional[ExcelValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or ExcelValidator()

    def get_all_worksheets(self) -> List[Dict[str, Any]]:
        """List all worksheets in active workbook with metadata."""
        def _sta_get_all() -> List[Dict[str, Any]]:
            wb = self.adapter.get_active_workbook_raw()
            if wb is None:
                raise ExcelNoActiveWorkbookError()

            sheets = []
            for ws in wb.Worksheets:
                meta = ExcelMetadataExtractor.extract_worksheet_metadata(ws)
                sheets.append(meta.model_dump())
            return sheets

        return self.worker.run(_sta_get_all)

    def get_active_worksheet_metadata(self) -> Dict[str, Any]:
        """Get metadata for the currently active sheet."""
        def _sta_active() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorkbookError()
            meta = ExcelMetadataExtractor.extract_worksheet_metadata(ws)
            return meta.model_dump()

        return self.worker.run(_sta_active)

    def create_worksheet(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new worksheet and optionally name it."""
        if name:
            name = self.validator.validate_worksheet_name(name)

        def _sta_create() -> Dict[str, Any]:
            wb = self.adapter.get_active_workbook_raw()
            if wb is None:
                raise ExcelNoActiveWorkbookError()

            # Add worksheet after last sheet
            last_sheet = wb.Worksheets(wb.Worksheets.Count)
            ws = wb.Worksheets.Add(After=last_sheet)
            if name:
                # Check for existing name collision
                existing = [s.Name.lower() for s in wb.Worksheets]
                if name.lower() in existing:
                    raise ExcelSecurityError(f"Worksheet '{name}' already exists.")
                ws.Name = name

            return {
                "status": "SUCCESS",
                "sheet_name": ws.Name,
                "index": ws.Index,
            }

        return self.worker.run(_sta_create)

    def rename_worksheet(self, old_name: str, new_name: str) -> Dict[str, Any]:
        """Rename an existing worksheet."""
        valid_new = self.validator.validate_worksheet_name(new_name)

        def _sta_rename() -> Dict[str, Any]:
            wb = self.adapter.get_active_workbook_raw()
            if wb is None:
                raise ExcelNoActiveWorkbookError()

            target_ws = None
            for s in wb.Worksheets:
                if s.Name.lower() == old_name.lower():
                    target_ws = s
                    break

            if target_ws is None:
                raise ExcelSheetNotFoundError(old_name)

            target_ws.Name = valid_new
            return {
                "status": "SUCCESS",
                "old_name": old_name,
                "new_name": valid_new,
            }

        return self.worker.run(_sta_rename)

    def delete_worksheet(self, name: str, confirmed: bool = False) -> Dict[str, Any]:
        """Delete a worksheet with explicit confirmation enforcement."""
        ExcelPermissionEngine.enforce_confirmation("excel_delete_worksheet", confirmed)

        def _sta_delete() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            wb = self.adapter.get_active_workbook_raw()
            if wb is None:
                raise ExcelNoActiveWorkbookError()

            if wb.Worksheets.Count <= 1:
                raise ExcelSecurityError("Cannot delete the only worksheet in a workbook.")

            target_ws = None
            for s in wb.Worksheets:
                if s.Name.lower() == name.lower():
                    target_ws = s
                    break

            if target_ws is None:
                raise ExcelSheetNotFoundError(name)

            # Suppress Excel delete confirmation dialog
            orig_alerts = app.DisplayAlerts
            try:
                app.DisplayAlerts = False
                target_ws.Delete()
            finally:
                app.DisplayAlerts = orig_alerts

            return {
                "status": "SUCCESS",
                "deleted_sheet": name,
                "remaining_sheet_count": wb.Worksheets.Count,
            }

        return self.worker.run(_sta_delete)

    def duplicate_worksheet(self, name: str, new_name: Optional[str] = None) -> Dict[str, Any]:
        """Duplicate a worksheet."""
        if new_name:
            new_name = self.validator.validate_worksheet_name(new_name)

        def _sta_dup() -> Dict[str, Any]:
            wb = self.adapter.get_active_workbook_raw()
            if wb is None:
                raise ExcelNoActiveWorkbookError()

            target_ws = None
            for s in wb.Worksheets:
                if s.Name.lower() == name.lower():
                    target_ws = s
                    break

            if target_ws is None:
                raise ExcelSheetNotFoundError(name)

            target_ws.Copy(After=target_ws)
            copied_ws = wb.Worksheets(target_ws.Index + 1)
            if new_name:
                copied_ws.Name = new_name

            return {
                "status": "SUCCESS",
                "original_sheet": name,
                "new_sheet_name": copied_ws.Name,
            }

        return self.worker.run(_sta_dup)

    def set_freeze_panes(self, cell_reference: str = "A2") -> Dict[str, Any]:
        """Freeze panes at specified cell reference (e.g. A2 to freeze header row)."""
        valid_cell = self.validator.validate_cell_address(cell_reference)

        def _sta_freeze() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorkbookError()

            app.ActiveWindow.FreezePanes = False
            ws.Range(valid_cell).Select()
            app.ActiveWindow.FreezePanes = True

            return {
                "status": "SUCCESS",
                "freeze_cell": valid_cell,
                "sheet_name": ws.Name,
            }

        return self.worker.run(_sta_freeze)

    def set_tab_color(self, name: str, color_int: int) -> Dict[str, Any]:
        """Set tab color of a worksheet (BGR integer)."""
        def _sta_color() -> Dict[str, Any]:
            wb = self.adapter.get_active_workbook_raw()
            if wb is None:
                raise ExcelNoActiveWorkbookError()

            target_ws = None
            for s in wb.Worksheets:
                if s.Name.lower() == name.lower():
                    target_ws = s
                    break

            if target_ws is None:
                raise ExcelSheetNotFoundError(name)

            target_ws.Tab.Color = color_int
            return {
                "status": "SUCCESS",
                "sheet_name": target_ws.Name,
                "tab_color": color_int,
            }

        return self.worker.run(_sta_color)
