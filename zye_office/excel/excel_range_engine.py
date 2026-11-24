"""
Range Operations & Bulk Data Engine for Microsoft Excel — Zye Day 22.
Provides high-performance 2D bulk array reads and writes across Excel cell grids.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union
from zye_office.excel.excel_adapter import ExcelAdapter
from zye_office.excel.excel_errors import (
    ExcelNoActiveWorksheetError,
    ExcelSecurityError,
    ExcelSheetProtectedError,
)
from zye_office.excel.excel_permissions import ExcelPermissionEngine
from zye_office.excel.excel_validator import ExcelValidator

logger = logging.getLogger("zye.office.excel.range")


class ExcelRangeEngine:
    """Performs bulk range reading, matrix writing, and structural row/column modifications."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        validator: Optional[ExcelValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or ExcelValidator()

    def get_range_values(self, range_reference: str) -> Dict[str, Any]:
        """Read 2D array of values in bulk from specified range."""
        valid_range = self.validator.validate_range_address(range_reference)

        def _sta_get_range() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            rng = ws.Range(valid_range)
            raw = rng.Value
            # COM returns either a single scalar or a tuple of tuples
            if isinstance(raw, tuple):
                values = [list(row) if isinstance(row, tuple) else [row] for row in raw]
            elif raw is None:
                values = [[None]]
            else:
                values = [[raw]]

            return {
                "status": "SUCCESS",
                "range": valid_range,
                "row_count": rng.Rows.Count,
                "column_count": rng.Columns.Count,
                "values": values,
            }

        return self.worker.run(_sta_get_range)

    def set_range_values(self, range_reference: str, data: List[List[Any]]) -> Dict[str, Any]:
        """Write a 2D matrix of values in a single high-performance COM call."""
        valid_range = self.validator.validate_range_address(range_reference)
        if not data or not isinstance(data, list):
            raise ExcelSecurityError("Data must be a non-empty 2D list of row values.")

        def _sta_set_range() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            # Convert 2D python list to nested tuple for win32com variant array write
            tuple_data = tuple(tuple(row) for row in data)
            rng = ws.Range(valid_range)

            # If range is single cell top-left, resize to match data dimensions
            rows_data = len(data)
            cols_data = len(data[0]) if rows_data > 0 else 0
            if ":" not in valid_range:
                target_rng = ws.Range(rng.Cells(1, 1), rng.Cells(rows_data, cols_data))
                target_rng.Value = tuple_data
                out_addr = target_rng.Address
            else:
                rng.Value = tuple_data
                out_addr = rng.Address

            return {
                "status": "SUCCESS",
                "range": out_addr,
                "rows_written": rows_data,
                "columns_written": cols_data,
            }

        return self.worker.run(_sta_set_range)

    def get_range_formulas(self, range_reference: str) -> Dict[str, Any]:
        """Read 2D array of formulas from specified range."""
        valid_range = self.validator.validate_range_address(range_reference)

        def _sta_get_formulas() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            rng = ws.Range(valid_range)
            raw = rng.Formula
            if isinstance(raw, tuple):
                formulas = [list(row) if isinstance(row, tuple) else [row] for row in raw]
            elif raw is None:
                formulas = [[None]]
            else:
                formulas = [[raw]]

            return {
                "status": "SUCCESS",
                "range": valid_range,
                "formulas": formulas,
            }

        return self.worker.run(_sta_get_formulas)

    def clear_range_contents(self, range_reference: str) -> Dict[str, Any]:
        """Clear contents of a range preserving borders and styling."""
        valid_range = self.validator.validate_range_address(range_reference)

        def _sta_clear() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            ws.Range(valid_range).ClearContents()
            return {
                "status": "SUCCESS",
                "range": valid_range,
                "cleared": True,
            }

        return self.worker.run(_sta_clear)

    def copy_range(self, source_range: str, destination_range: str) -> Dict[str, Any]:
        """Copy a range to a destination range."""
        valid_src = self.validator.validate_range_address(source_range)
        valid_dest = self.validator.validate_range_address(destination_range)

        def _sta_copy() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            ws.Range(valid_src).Copy(Destination=ws.Range(valid_dest))
            return {
                "status": "SUCCESS",
                "source": valid_src,
                "destination": valid_dest,
            }

        return self.worker.run(_sta_copy)

    def insert_rows(self, row_number: int, count: int = 1) -> Dict[str, Any]:
        """Insert one or more blank rows at row_number."""
        if row_number < 1:
            raise ExcelSecurityError("Row number must be >= 1.")

        def _sta_insert_r() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            for _ in range(count):
                ws.Rows(row_number).Insert()

            return {
                "status": "SUCCESS",
                "inserted_at_row": row_number,
                "count": count,
            }

        return self.worker.run(_sta_insert_r)

    def delete_rows(self, row_number: int, count: int = 1, confirmed: bool = False) -> Dict[str, Any]:
        """Delete one or more rows with explicit confirmation."""
        ExcelPermissionEngine.enforce_confirmation("excel_delete_rows", confirmed)

        def _sta_del_r() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            for _ in range(count):
                ws.Rows(row_number).Delete()

            return {
                "status": "SUCCESS",
                "deleted_at_row": row_number,
                "count": count,
            }

        return self.worker.run(_sta_del_r)

    def insert_columns(self, column_number: int, count: int = 1) -> Dict[str, Any]:
        """Insert one or more blank columns at column_number."""
        if column_number < 1:
            raise ExcelSecurityError("Column number must be >= 1.")

        def _sta_insert_c() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            for _ in range(count):
                ws.Columns(column_number).Insert()

            return {
                "status": "SUCCESS",
                "inserted_at_column": column_number,
                "count": count,
            }

        return self.worker.run(_sta_insert_c)

    def delete_columns(self, column_number: int, count: int = 1, confirmed: bool = False) -> Dict[str, Any]:
        """Delete one or more columns with explicit confirmation."""
        ExcelPermissionEngine.enforce_confirmation("excel_delete_columns", confirmed)

        def _sta_del_c() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            for _ in range(count):
                ws.Columns(column_number).Delete()

            return {
                "status": "SUCCESS",
                "deleted_at_column": column_number,
                "count": count,
            }

        return self.worker.run(_sta_del_c)

    def merge_cells(self, range_reference: str) -> Dict[str, Any]:
        """Merge a range of cells."""
        valid_range = self.validator.validate_range_address(range_reference)

        def _sta_merge() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            ws.Range(valid_range).Merge()
            return {
                "status": "SUCCESS",
                "range": valid_range,
                "merged": True,
            }

        return self.worker.run(_sta_merge)

    def unmerge_cells(self, range_reference: str) -> Dict[str, Any]:
        """Unmerge a range of cells."""
        valid_range = self.validator.validate_range_address(range_reference)

        def _sta_unmerge() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            ws.Range(valid_range).UnMerge()
            return {
                "status": "SUCCESS",
                "range": valid_range,
                "unmerged": True,
            }

        return self.worker.run(_sta_unmerge)
