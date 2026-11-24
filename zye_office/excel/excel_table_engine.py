"""
Excel Table (ListObject) Engine for Microsoft Excel — Zye Day 22.
Creates and manages structured Excel Tables, total rows, styles, and row expansions.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.excel.excel_adapter import ExcelAdapter
from zye_office.excel.excel_errors import (
    ExcelNoActiveWorksheetError,
    ExcelSecurityError,
    ExcelSheetProtectedError,
)
from zye_office.excel.excel_validator import ExcelValidator

logger = logging.getLogger("zye.office.excel.table")


class ExcelTableEngine:
    """Manages Excel ListObjects (Tables) and structured referencing."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        validator: Optional[ExcelValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or ExcelValidator()

    def create_table(
        self,
        range_address: str,
        table_name: Optional[str] = None,
        style_name: str = "TableStyleMedium9",
        show_headers: bool = True,
        show_totals: bool = False,
    ) -> Dict[str, Any]:
        """Convert a range into a formatted Excel ListObject (Table)."""
        valid_range = self.validator.validate_range_address(range_address)

        def _sta_create_table() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range)
            # xlSrcRange = 1, xlYes = 1, xlNo = 2
            has_headers = 1 if show_headers else 2
            tbl = ws.ListObjects.Add(
                1,  # SourceType: xlSrcRange
                rng,
                None,
                has_headers,
            )

            if table_name:
                tbl.Name = table_name
            if style_name:
                try:
                    tbl.TableStyle = style_name
                except Exception:
                    pass
            if show_totals:
                tbl.ShowTotals = True

            return {
                "status": "SUCCESS",
                "table_name": tbl.Name,
                "range": tbl.Range.Address,
                "has_headers": show_headers,
                "show_totals": show_totals,
                "style": style_name,
            }

        return self.worker.run(_sta_create_table)

    def get_tables(self) -> Dict[str, Any]:
        """List all structured tables in active worksheet."""
        def _sta_get_tables() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            tables = []
            for i in range(1, ws.ListObjects.Count + 1):
                t = ws.ListObjects(i)
                tables.append({
                    "name": t.Name,
                    "range": t.Range.Address,
                    "data_body_range": t.DataBodyRange.Address if t.DataBodyRange else None,
                    "row_count": t.ListRows.Count,
                    "column_count": t.ListColumns.Count,
                    "show_totals": t.ShowTotals,
                })

            return {
                "status": "SUCCESS",
                "total_tables": len(tables),
                "tables": tables,
            }

        return self.worker.run(_sta_get_tables)

    def set_table_style(self, table_name: str, style_name: str) -> Dict[str, Any]:
        """Change visual style of an Excel Table."""
        def _sta_style() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            tbl = ws.ListObjects(table_name)
            tbl.TableStyle = style_name
            return {
                "status": "SUCCESS",
                "table_name": table_name,
                "style": style_name,
            }

        return self.worker.run(_sta_style)

    def set_table_total_row(self, table_name: str, show_totals: bool = True) -> Dict[str, Any]:
        """Enable or disable the totals summary row at the bottom of the table."""
        def _sta_totals() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            tbl = ws.ListObjects(table_name)
            tbl.ShowTotals = show_totals
            return {
                "status": "SUCCESS",
                "table_name": table_name,
                "show_totals": show_totals,
            }

        return self.worker.run(_sta_totals)

    def remove_table(self, table_name: str, keep_data: bool = True) -> Dict[str, Any]:
        """Unlist table back to normal cells (or delete)."""
        def _sta_remove() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            tbl = ws.ListObjects(table_name)
            addr = tbl.Range.Address
            if keep_data:
                tbl.Unlink()
            else:
                tbl.Delete()

            return {
                "status": "SUCCESS",
                "table_name": table_name,
                "range": addr,
                "data_preserved": keep_data,
            }

        return self.worker.run(_sta_remove)
