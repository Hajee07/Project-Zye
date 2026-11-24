"""
Formula Auditing & Error Detection Engine for Microsoft Excel — Zye Day 22.
Detects #REF!, #DIV/0!, #VALUE!, #NAME?, #N/A, #NUM!, #NULL! and suggests corrections.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.excel.excel_adapter import ExcelAdapter
from zye_office.excel.excel_errors import ExcelNoActiveWorksheetError
from zye_office.excel.excel_validator import ExcelValidator

logger = logging.getLogger("zye.office.excel.formula_auditor")

ERROR_SEVERITY_MAP = {
    "#REF!": ("CRITICAL", "A cell referenced in this formula was moved or deleted. Re-point formula to valid cells."),
    "#DIV/0!": ("HIGH", "Formula attempted division by zero or an empty cell. Wrap in IFERROR or check denominator."),
    "#VALUE!": ("HIGH", "Wrong argument or operand data type (e.g. text in mathematical function). Verify inputs."),
    "#NAME?": ("HIGH", "Unrecognized formula name or unquoted text. Verify spelling of Excel function name."),
    "#NUM!": ("MEDIUM", "Numeric value is out of valid Excel mathematical bounds or iterative calculation failed."),
    "#N/A": ("MEDIUM", "Lookup value was not found (e.g. in VLOOKUP/XLOOKUP). Check lookup key or wrap in IFNA."),
    "#NULL!": ("LOW", "Intersection of two ranges that do not intersect. Check range separator spaces."),
}


class ExcelFormulaAuditor:
    """Scans worksheet ranges to detect broken formulas and return diagnostic reports."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        validator: Optional[ExcelValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or ExcelValidator()

    def audit_formula_range(self, range_address: Optional[str] = None) -> Dict[str, Any]:
        """Audit formulas in the specified range (or entire active worksheet UsedRange)."""
        valid_range = self.validator.validate_range_address(range_address) if range_address else None

        def _sta_audit() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            rng = ws.Range(valid_range) if valid_range else ws.UsedRange
            total_cells = rng.Cells.Count
            formula_count = 0
            errors_detected: List[Dict[str, Any]] = []

            # Use SpecialCells(xlCellTypeFormulas = -4123) for fast scanning
            try:
                formula_cells = rng.SpecialCells(-4123)
            except Exception:
                # No formulas in range
                return {
                    "status": "SUCCESS",
                    "scanned_range": rng.Address,
                    "total_cells": total_cells,
                    "formula_count": 0,
                    "error_count": 0,
                    "errors": [],
                    "health": "HEALTHY",
                }

            # Iterate through formula cells
            for cell in formula_cells:
                formula_count += 1
                val_str = str(cell.Value) if cell.Value is not None else ""
                for err_code, (sev, rec) in ERROR_SEVERITY_MAP.items():
                    if err_code in val_str:
                        errors_detected.append({
                            "cell": cell.Address,
                            "formula": cell.Formula,
                            "error_code": err_code,
                            "severity": sev,
                            "remediation": rec,
                        })
                        break

            health = "HEALTHY" if len(errors_detected) == 0 else ("CRITICAL" if any(e["severity"] == "CRITICAL" for e in errors_detected) else "ATTENTION_REQUIRED")

            return {
                "status": "SUCCESS",
                "scanned_range": rng.Address,
                "total_cells": total_cells,
                "formula_count": formula_count,
                "error_count": len(errors_detected),
                "health": health,
                "errors": errors_detected,
            }

        return self.worker.run(_sta_audit)

    def find_formula_errors(self, range_address: Optional[str] = None) -> Dict[str, Any]:
        """Convenience method returning list of cells with evaluated Excel formula errors."""
        audit_res = self.audit_formula_range(range_address)
        return {
            "status": "SUCCESS",
            "error_count": audit_res.get("error_count", 0),
            "errors": audit_res.get("errors", []),
        }
