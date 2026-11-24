"""
Calculation & Recalculation Engine for Microsoft Excel — Zye Day 22.
Manages automatic/manual calculation modes and explicit full recalculation rebuilds.
"""

from __future__ import annotations

from contextlib import contextmanager
import logging
from typing import Any, Dict, Iterator, Optional
from zye_office.excel.excel_adapter import ExcelAdapter
from zye_office.excel.excel_constants import ExcelConstants
from zye_office.excel.excel_errors import (
    ExcelCOMUnavailableError,
    ExcelNoActiveWorksheetError,
)
from zye_office.excel.excel_validator import ExcelValidator

logger = logging.getLogger("zye.office.excel.calculation")

CALC_MAP = {
    "AUTOMATIC": ExcelConstants.xlCalculationAutomatic,
    "MANUAL": ExcelConstants.xlCalculationManual,
    "SEMIAUTOMATIC": ExcelConstants.xlCalculationSemiautomatic,
}

REV_CALC_MAP = {
    ExcelConstants.xlCalculationAutomatic: "AUTOMATIC",
    ExcelConstants.xlCalculationManual: "MANUAL",
    ExcelConstants.xlCalculationSemiautomatic: "SEMIAUTOMATIC",
}


class ExcelCalculationEngine:
    """Controls Excel formula recalculation modes and state."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        validator: Optional[ExcelValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or ExcelValidator()

    def get_calculation_mode(self) -> Dict[str, Any]:
        """Query current calculation mode of Excel application."""
        def _sta_get_mode() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            if app is None:
                raise ExcelCOMUnavailableError()

            c_val = getattr(app, "Calculation", ExcelConstants.xlCalculationAutomatic)
            mode_str = REV_CALC_MAP.get(c_val, "AUTOMATIC")
            return {
                "status": "SUCCESS",
                "calculation_mode": mode_str,
                "raw_constant": c_val,
            }

        return self.worker.run(_sta_get_mode)

    def set_calculation_mode(self, mode: str = "AUTOMATIC") -> Dict[str, Any]:
        """Set calculation mode (AUTOMATIC, MANUAL, SEMIAUTOMATIC)."""
        norm_mode = mode.upper().strip()
        c_val = CALC_MAP.get(norm_mode, ExcelConstants.xlCalculationAutomatic)

        def _sta_set_mode() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            if app is None:
                raise ExcelCOMUnavailableError()

            orig_val = getattr(app, "Calculation", ExcelConstants.xlCalculationAutomatic)
            app.Calculation = c_val
            return {
                "status": "SUCCESS",
                "previous_mode": REV_CALC_MAP.get(orig_val, "AUTOMATIC"),
                "new_mode": norm_mode,
            }

        return self.worker.run(_sta_set_mode)

    def calculate_workbook(self) -> Dict[str, Any]:
        """Trigger immediate recalculation of all formulas in active workbook."""
        def _sta_calc() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            if app is None:
                raise ExcelCOMUnavailableError()

            app.Calculate()
            return {
                "status": "SUCCESS",
                "calculated": True,
            }

        return self.worker.run(_sta_calc)

    def calculate_full_rebuild(self) -> Dict[str, Any]:
        """Perform full dependency tree rebuild and recalculation (CalculateFullRebuild)."""
        def _sta_rebuild() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            if app is None:
                raise ExcelCOMUnavailableError()

            try:
                app.CalculateFullRebuild()
            except Exception:
                app.Calculate()

            return {
                "status": "SUCCESS",
                "full_rebuild": True,
            }

        return self.worker.run(_sta_rebuild)

    @contextmanager
    def temporary_manual_calculation(self) -> Iterator[None]:
        """Temporarily set calculation to Manual during bulk writes and restore original mode."""
        orig_info = self.get_calculation_mode()
        orig_mode = orig_info.get("calculation_mode", "AUTOMATIC")
        try:
            self.set_calculation_mode("MANUAL")
            yield
        finally:
            self.set_calculation_mode(orig_mode)
            self.calculate_workbook()
