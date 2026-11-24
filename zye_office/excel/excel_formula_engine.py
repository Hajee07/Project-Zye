"""
Advanced Formula Engine for Microsoft Excel — Zye Day 22.
Supports mathematical, statistical, logical, lookup, dynamic array functions, and autofill.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.excel.excel_adapter import ExcelAdapter
from zye_office.excel.excel_errors import (
    ExcelFormulaInvalidError,
    ExcelFormulaResultError,
    ExcelNoActiveWorksheetError,
    ExcelSheetProtectedError,
)
from zye_office.excel.excel_validator import ExcelValidator

logger = logging.getLogger("zye.office.excel.formula")

EXCEL_ERROR_VALUES = {"#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!", "#NULL!"}


class ExcelFormulaEngine:
    """Manages formula insertion, autofill, precedents, and evaluation in Excel."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        validator: Optional[ExcelValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or ExcelValidator()

    def insert_formula(self, cell: str, formula: str) -> Dict[str, Any]:
        """Insert a validated formula into a single cell and verify evaluated result."""
        valid_cell = self.validator.validate_cell_address(cell)
        valid_formula = self.validator.validate_formula(formula)

        def _sta_insert() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            c = ws.Range(valid_cell)
            c.Formula = valid_formula
            val = str(c.Value) if c.Value is not None else ""

            # Check if formula immediately evaluated to an error code
            is_error = any(err in val for err in EXCEL_ERROR_VALUES)
            return {
                "status": "SUCCESS",
                "cell": valid_cell,
                "formula": valid_formula,
                "result": c.Value,
                "has_error": is_error,
                "error_value": val if is_error else None,
            }

        return self.worker.run(_sta_insert)

    def insert_formula_range(self, range_address: str, formula: str) -> Dict[str, Any]:
        """Apply a formula across an entire range (Excel relative reference expansion)."""
        valid_range = self.validator.validate_range_address(range_address)
        valid_formula = self.validator.validate_formula(formula)

        def _sta_range_formula() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range)
            rng.Formula = valid_formula
            return {
                "status": "SUCCESS",
                "range": valid_range,
                "formula": valid_formula,
                "cells_affected": rng.Cells.Count,
            }

        return self.worker.run(_sta_range_formula)

    def fill_formula_down(self, range_address: str) -> Dict[str, Any]:
        """Fill formula from top cell down throughout specified range."""
        valid_range = self.validator.validate_range_address(range_address)

        def _sta_fill_down() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range)
            rng.FillDown()
            return {
                "status": "SUCCESS",
                "range": valid_range,
                "fill_direction": "DOWN",
            }

        return self.worker.run(_sta_fill_down)

    def fill_formula_right(self, range_address: str) -> Dict[str, Any]:
        """Fill formula from leftmost cell rightwards throughout range."""
        valid_range = self.validator.validate_range_address(range_address)

        def _sta_fill_right() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range)
            rng.FillRight()
            return {
                "status": "SUCCESS",
                "range": valid_range,
                "fill_direction": "RIGHT",
            }

        return self.worker.run(_sta_fill_right)

    def convert_formula_to_value(self, range_address: str) -> Dict[str, Any]:
        """Freeze formulas into static evaluated values (Copy -> Paste Special Values)."""
        valid_range = self.validator.validate_range_address(range_address)

        def _sta_freeze() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range)
            rng.Value = rng.Value  # Freezes formulas in-place
            return {
                "status": "SUCCESS",
                "range": valid_range,
                "converted_to_values": True,
            }

        return self.worker.run(_sta_freeze)

    def get_formula_precedents(self, cell: str) -> Dict[str, Any]:
        """Inspect cells that feed directly into the target formula cell."""
        valid_cell = self.validator.validate_cell_address(cell)

        def _sta_precedents() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            c = ws.Range(valid_cell)
            if not c.HasFormula:
                return {"status": "SUCCESS", "cell": valid_cell, "has_formula": False, "precedents": []}

            prec_addrs = []
            try:
                prec = c.Precedents
                if prec:
                    for area in prec.Areas:
                        prec_addrs.append(area.Address)
            except Exception:
                pass

            return {
                "status": "SUCCESS",
                "cell": valid_cell,
                "formula": c.Formula,
                "precedents": prec_addrs,
            }

        return self.worker.run(_sta_precedents)

    def get_formula_dependents(self, cell: str) -> Dict[str, Any]:
        """Inspect cells that depend on the target cell."""
        valid_cell = self.validator.validate_cell_address(cell)

        def _sta_dependents() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            c = ws.Range(valid_cell)
            dep_addrs = []
            try:
                deps = c.Dependents
                if deps:
                    for area in deps.Areas:
                        dep_addrs.append(area.Address)
            except Exception:
                pass

            return {
                "status": "SUCCESS",
                "cell": valid_cell,
                "dependents": dep_addrs,
            }

        return self.worker.run(_sta_dependents)
