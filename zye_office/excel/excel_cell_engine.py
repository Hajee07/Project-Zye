"""
Cell Operations Engine for Microsoft Excel — Zye Day 22.
Handles single-cell reads, writes, formulas, formatting queries, and clearing.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from zye_office.excel.excel_adapter import ExcelAdapter
from zye_office.excel.excel_errors import (
    ExcelNoActiveWorksheetError,
    ExcelSheetProtectedError,
)
from zye_office.models.excel_models import ExcelCellMetadata
from zye_office.excel.excel_validator import ExcelValidator

logger = logging.getLogger("zye.office.excel.cell")


class ExcelCellEngine:
    """Manages single-cell read/write operations inside active worksheet."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        validator: Optional[ExcelValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or ExcelValidator()

    def get_cell_value(self, cell_reference: str) -> Dict[str, Any]:
        """Read value of a single cell."""
        valid_cell = self.validator.validate_cell_address(cell_reference)

        def _sta_get() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            c = ws.Range(valid_cell)
            return {
                "status": "SUCCESS",
                "cell": valid_cell,
                "value": c.Value,
                "has_formula": bool(c.HasFormula),
                "formula": c.Formula if c.HasFormula else None,
            }

        return self.worker.run(_sta_get)

    def get_cell_formula(self, cell_reference: str) -> Dict[str, Any]:
        """Read formula of a single cell."""
        valid_cell = self.validator.validate_cell_address(cell_reference)

        def _sta_get_formula() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            c = ws.Range(valid_cell)
            return {
                "status": "SUCCESS",
                "cell": valid_cell,
                "has_formula": bool(c.HasFormula),
                "formula": c.Formula if c.HasFormula else None,
                "result_value": c.Value,
            }

        return self.worker.run(_sta_get_formula)

    def set_cell_value(self, cell_reference: str, value: Any) -> Dict[str, Any]:
        """Write a value (string, number, boolean) into a cell."""
        valid_cell = self.validator.validate_cell_address(cell_reference)

        def _sta_set() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            c = ws.Range(valid_cell)
            c.Value = value
            return {
                "status": "SUCCESS",
                "cell": valid_cell,
                "assigned_value": value,
                "resulting_value": c.Value,
            }

        return self.worker.run(_sta_set)

    def set_cell_formula(self, cell_reference: str, formula: str) -> Dict[str, Any]:
        """Write an Excel formula into a cell with validation."""
        valid_cell = self.validator.validate_cell_address(cell_reference)
        valid_formula = self.validator.validate_formula(formula)

        def _sta_set_formula() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            c = ws.Range(valid_cell)
            c.Formula = valid_formula
            return {
                "status": "SUCCESS",
                "cell": valid_cell,
                "formula": valid_formula,
                "evaluated_value": c.Value,
            }

        return self.worker.run(_sta_set_formula)

    def clear_cell_contents(self, cell_reference: str) -> Dict[str, Any]:
        """Clear the content of a cell preserving formatting."""
        valid_cell = self.validator.validate_cell_address(cell_reference)

        def _sta_clear() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            c = ws.Range(valid_cell)
            c.ClearContents()
            return {
                "status": "SUCCESS",
                "cell": valid_cell,
                "cleared": True,
            }

        return self.worker.run(_sta_clear)

    def get_cell_metadata(self, cell_reference: str) -> Dict[str, Any]:
        """Get cell formatting, coordinates, formula, and value."""
        valid_cell = self.validator.validate_cell_address(cell_reference)

        def _sta_meta() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            c = ws.Range(valid_cell)
            meta = ExcelCellMetadata(
                status="SUCCESS",
                address=valid_cell,
                row=c.Row,
                column=c.Column,
                value=c.Value,
                formula=c.Formula if c.HasFormula else None,
                has_formula=bool(c.HasFormula),
                number_format=str(c.NumberFormat),
                font_name=getattr(c.Font, "Name", None),
                font_size=getattr(c.Font, "Size", None),
                bold=getattr(c.Font, "Bold", None),
                italic=getattr(c.Font, "Italic", None),
                color=getattr(c.Font, "Color", None),
                bg_color=getattr(c.Interior, "Color", None),
            )
            return meta.model_dump()

        return self.worker.run(_sta_meta)
