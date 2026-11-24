"""
Native Conditional Formatting Engine for Microsoft Excel — Zye Day 22.
Applies dynamic visual rules: cell values, formulas, duplicates, color scales, and data bars.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.excel.excel_adapter import ExcelAdapter
from zye_office.excel.excel_constants import ExcelConstants
from zye_office.excel.excel_errors import (
    ExcelNoActiveWorksheetError,
    ExcelSheetProtectedError,
)
from zye_office.excel.excel_validator import ExcelValidator

logger = logging.getLogger("zye.office.excel.conditional_formatting")

CF_OP_MAP = {
    "between": ExcelConstants.xlBetween,
    "not_between": ExcelConstants.xlNotBetween,
    "equal": ExcelConstants.xlEqual,
    "not_equal": ExcelConstants.xlNotEqual,
    "greater_than": ExcelConstants.xlGreater,
    "less_than": ExcelConstants.xlLess,
    "greater_equal": ExcelConstants.xlGreaterEqual,
    "less_equal": ExcelConstants.xlLessEqual,
}


class ExcelConditionalFormattingEngine:
    """Manages Excel FormatConditions collection natively."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        validator: Optional[ExcelValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or ExcelValidator()

    def add_cell_value_rule(
        self,
        range_address: str,
        operator: str,
        formula1: str,
        formula2: Optional[str] = None,
        font_color: Optional[int] = None,
        bg_color: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Add cell value comparison rule (e.g. less_than 0 -> red fill)."""
        valid_range = self.validator.validate_range_address(range_address)
        op_val = CF_OP_MAP.get(operator.lower(), ExcelConstants.xlGreater)

        def _sta_add_cell_val() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range)
            # Add(Type=xlCellValue, Operator=op_val, Formula1=formula1, Formula2=formula2)
            f_cond = rng.FormatConditions.Add(
                Type=ExcelConstants.xlCellValue,
                Operator=op_val,
                Formula1=str(formula1),
                Formula2=str(formula2) if formula2 else None,
            )
            if bg_color is not None:
                f_cond.Interior.Color = bg_color
            if font_color is not None:
                f_cond.Font.Color = font_color

            return {
                "status": "SUCCESS",
                "range": valid_range,
                "rule_type": "CELL_VALUE",
                "operator": operator,
                "formula1": formula1,
                "formula2": formula2,
            }

        return self.worker.run(_sta_add_cell_val)

    def add_formula_rule(
        self,
        range_address: str,
        formula: str,
        font_color: Optional[int] = None,
        bg_color: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Add expression/formula-based conditional formatting rule."""
        valid_range = self.validator.validate_range_address(range_address)
        valid_formula = self.validator.validate_formula(formula)

        def _sta_add_formula() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range)
            f_cond = rng.FormatConditions.Add(
                Type=ExcelConstants.xlExpression,
                Formula1=valid_formula,
            )
            if bg_color is not None:
                f_cond.Interior.Color = bg_color
            if font_color is not None:
                f_cond.Font.Color = font_color

            return {
                "status": "SUCCESS",
                "range": valid_range,
                "rule_type": "FORMULA",
                "formula": valid_formula,
            }

        return self.worker.run(_sta_add_formula)

    def add_duplicate_value_rule(
        self,
        range_address: str,
        font_color: Optional[int] = None,
        bg_color: Optional[int] = 13551615,  # Soft red
    ) -> Dict[str, Any]:
        """Highlight duplicate values in specified range."""
        valid_range = self.validator.validate_range_address(range_address)

        def _sta_dup() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range)
            # AddUniqueValues
            f_cond = rng.FormatConditions.AddUniqueValues()
            # DupeCondition = xlDuplicate (1)
            f_cond.DupeUnique = 1
            if bg_color is not None:
                f_cond.Interior.Color = bg_color
            if font_color is not None:
                f_cond.Font.Color = font_color

            return {
                "status": "SUCCESS",
                "range": valid_range,
                "rule_type": "DUPLICATE_VALUES",
            }

        return self.worker.run(_sta_dup)

    def add_color_scale_rule(self, range_address: str) -> Dict[str, Any]:
        """Apply a 3-color scale (Green - Yellow - Red heatmap) to range."""
        valid_range = self.validator.validate_range_address(range_address)

        def _sta_scale() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range)
            # AddColorScale(ColorScaleType=3)
            f_cond = rng.FormatConditions.AddColorScale(ColorScaleType=3)
            return {
                "status": "SUCCESS",
                "range": valid_range,
                "rule_type": "COLOR_SCALE_3",
            }

        return self.worker.run(_sta_scale)

    def add_data_bar_rule(self, range_address: str, color_bgr: int = 16751001) -> Dict[str, Any]:
        """Add horizontal in-cell data bars reflecting numeric magnitudes."""
        valid_range = self.validator.validate_range_address(range_address)

        def _sta_databar() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range)
            f_cond = rng.FormatConditions.AddDatabar()
            try:
                f_cond.BarColor.Color = color_bgr
            except Exception:
                pass

            return {
                "status": "SUCCESS",
                "range": valid_range,
                "rule_type": "DATA_BAR",
            }

        return self.worker.run(_sta_databar)

    def remove_conditional_formatting(self, range_address: Optional[str] = None) -> Dict[str, Any]:
        """Delete all conditional formatting rules from range (or entire sheet)."""
        valid_range = self.validator.validate_range_address(range_address) if range_address else None

        def _sta_remove() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range) if valid_range else ws.UsedRange
            rng.FormatConditions.Delete()
            return {
                "status": "SUCCESS",
                "range": rng.Address,
                "cleared": True,
            }

        return self.worker.run(_sta_remove)

    def get_conditional_formatting_rules(self, range_address: Optional[str] = None) -> Dict[str, Any]:
        """List active conditional formatting rules in range."""
        valid_range = self.validator.validate_range_address(range_address) if range_address else None

        def _sta_get_rules() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            rng = ws.Range(valid_range) if valid_range else ws.UsedRange
            count = getattr(rng.FormatConditions, "Count", 0)
            rules = []
            for i in range(1, count + 1):
                try:
                    c = rng.FormatConditions(i)
                    rules.append({
                        "index": i,
                        "type": getattr(c, "Type", None),
                        "operator": getattr(c, "Operator", None),
                        "formula1": getattr(c, "Formula1", None),
                        "stop_if_true": getattr(c, "StopIfTrue", True),
                    })
                except Exception:
                    pass

            return {
                "status": "SUCCESS",
                "range": rng.Address,
                "rules_count": count,
                "rules": rules,
            }

        return self.worker.run(_sta_get_rules)
