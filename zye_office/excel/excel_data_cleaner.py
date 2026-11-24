"""
Data Cleaning & Quality Engine for Microsoft Excel — Zye Day 22.
Trims whitespace, eliminates duplicates, removes blank rows, standardizes case, and audits data quality.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union
from zye_office.excel.excel_adapter import ExcelAdapter
from zye_office.excel.excel_errors import (
    ExcelNoActiveWorksheetError,
    ExcelSheetProtectedError,
)
from zye_office.excel.excel_permissions import ExcelPermissionEngine
from zye_office.excel.excel_validator import ExcelValidator

logger = logging.getLogger("zye.office.excel.data_cleaner")


class ExcelDataCleaner:
    """Manages data hygiene, duplicate removal, text trimming, and quality reporting."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        validator: Optional[ExcelValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or ExcelValidator()

    def trim_extra_spaces(self, range_address: Optional[str] = None) -> Dict[str, Any]:
        """Strip leading, trailing, and redundant internal whitespace from text cells."""
        valid_range = self.validator.validate_range_address(range_address) if range_address else None

        def _sta_trim() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range) if valid_range else ws.UsedRange
            raw_vals = rng.Value

            cells_modified = 0
            if isinstance(raw_vals, tuple):
                new_vals = []
                for row in raw_vals:
                    new_row = []
                    if isinstance(row, tuple):
                        for c in row:
                            if isinstance(c, str):
                                trimmed = " ".join(c.split())
                                if trimmed != c:
                                    cells_modified += 1
                                new_row.append(trimmed)
                            else:
                                new_row.append(c)
                    else:
                        if isinstance(row, str):
                            trimmed = " ".join(row.split())
                            if trimmed != row:
                                cells_modified += 1
                            new_row.append(trimmed)
                        else:
                            new_row.append(row)
                    new_vals.append(tuple(new_row))

                rng.Value = tuple(new_vals)

            return {
                "status": "SUCCESS",
                "range": rng.Address,
                "cells_trimmed": cells_modified,
            }

        return self.worker.run(_sta_trim)

    def remove_duplicates(
        self,
        range_address: Optional[str] = None,
        columns: Optional[List[int]] = None,
        has_headers: bool = True,
        confirmed: bool = False,
    ) -> Dict[str, Any]:
        """Remove duplicate rows using Excel native RemoveDuplicates."""
        ExcelPermissionEngine.enforce_confirmation("excel_remove_duplicates", confirmed)
        valid_range = self.validator.validate_range_address(range_address) if range_address else None

        def _sta_remove_dupes() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range) if valid_range else ws.UsedRange
            initial_rows = rng.Rows.Count

            # Columns array: 1-based index of columns to check
            if columns:
                cols_variant = list(columns)
            else:
                cols_variant = list(range(1, rng.Columns.Count + 1))

            # Header: xlYes = 1, xlNo = 2
            hdr = 1 if has_headers else 2
            rng.RemoveDuplicates(Columns=cols_variant, Header=hdr)

            # Re-read new row count
            new_rows = ws.Range(rng.Address).Rows.Count

            return {
                "status": "SUCCESS",
                "range": rng.Address,
                "initial_row_count": initial_rows,
                "new_row_count": new_rows,
                "duplicates_removed": max(0, initial_rows - new_rows),
            }

        return self.worker.run(_sta_remove_dupes)

    def standardize_text_case(
        self,
        range_address: str,
        case_type: str = "UPPER",
    ) -> Dict[str, Any]:
        """Convert text in range to UPPER, LOWER, or PROPER case."""
        valid_range = self.validator.validate_range_address(range_address)
        norm_case = case_type.upper().strip()

        def _sta_case() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range)
            raw = rng.Value
            cells_modified = 0

            if isinstance(raw, tuple):
                new_vals = []
                for row in raw:
                    new_row = []
                    for c in (row if isinstance(row, tuple) else [row]):
                        if isinstance(c, str):
                            if norm_case == "UPPER":
                                trans = c.upper()
                            elif norm_case == "LOWER":
                                trans = c.lower()
                            elif norm_case == "PROPER":
                                trans = c.title()
                            else:
                                trans = c
                            if trans != c:
                                cells_modified += 1
                            new_row.append(trans)
                        else:
                            new_row.append(c)
                    new_vals.append(tuple(new_row))

                rng.Value = tuple(new_vals)

            return {
                "status": "SUCCESS",
                "range": valid_range,
                "case_type": norm_case,
                "cells_modified": cells_modified,
            }

        return self.worker.run(_sta_case)

    def generate_data_quality_report(
        self,
        range_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate summary of missing values, blank rows, and data types across dataset."""
        valid_range = self.validator.validate_range_address(range_address) if range_address else None

        def _sta_report() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            rng = ws.Range(valid_range) if valid_range else ws.UsedRange
            total_cells = rng.Cells.Count
            raw = rng.Value

            empty_count = 0
            text_count = 0
            num_count = 0
            bool_count = 0

            if isinstance(raw, tuple):
                for row in raw:
                    for c in (row if isinstance(row, tuple) else [row]):
                        if c is None or c == "":
                            empty_count += 1
                        elif isinstance(c, (int, float)):
                            num_count += 1
                        elif isinstance(c, bool):
                            bool_count += 1
                        elif isinstance(c, str):
                            text_count += 1

            return {
                "status": "SUCCESS",
                "range": rng.Address,
                "total_rows": rng.Rows.Count,
                "total_columns": rng.Columns.Count,
                "total_cells": total_cells,
                "empty_cells": empty_count,
                "numeric_cells": num_count,
                "text_cells": text_count,
                "boolean_cells": bool_count,
                "completeness_percentage": round(((total_cells - empty_count) / max(1, total_cells)) * 100, 2),
            }

        return self.worker.run(_sta_report)
