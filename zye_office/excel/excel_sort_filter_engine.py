"""
Sorting & AutoFilter Engine for Microsoft Excel — Zye Day 22.
Enables multi-column ascending/descending sorting and dynamic AutoFilter criteria.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Union
from zye_office.excel.excel_adapter import ExcelAdapter
from zye_office.excel.excel_constants import ExcelConstants
from zye_office.excel.excel_errors import (
    ExcelNoActiveWorksheetError,
    ExcelSheetProtectedError,
)
from zye_office.excel.excel_validator import ExcelValidator
from zye_office.models.excel_models import ExcelSortConfig

logger = logging.getLogger("zye.office.excel.sort_filter")


class ExcelSortFilterEngine:
    """Manages sorting ranges and AutoFilter criteria."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        validator: Optional[ExcelValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or ExcelValidator()

    def sort_range(
        self,
        range_address: str,
        config: Union[ExcelSortConfig, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Sort range by specified key column and order."""
        valid_range = self.validator.validate_range_address(range_address)
        if isinstance(config, dict):
            cfg = ExcelSortConfig(**config)
        else:
            cfg = config

        order_val = ExcelConstants.xlAscending if cfg.order.lower() == "ascending" else ExcelConstants.xlDescending
        header_val = ExcelConstants.xlYes if cfg.has_headers else ExcelConstants.xlNo

        def _sta_sort() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range)

            # Resolve key cell
            if isinstance(cfg.key_column, str) and not cfg.key_column.isdigit():
                # E.g. "B" or "B1"
                col_letter = cfg.key_column.strip().replace("$", "")
                key_cell = ws.Range(f"{col_letter}1")
            else:
                col_idx = int(cfg.key_column)
                key_cell = rng.Columns(col_idx)

            rng.Sort(
                Key1=key_cell,
                Order1=order_val,
                Header=header_val,
                MatchCase=cfg.match_case,
                Orientation=1,  # xlSortRows
            )

            return {
                "status": "SUCCESS",
                "range": valid_range,
                "key_column": str(cfg.key_column),
                "order": cfg.order,
                "has_headers": cfg.has_headers,
            }

        return self.worker.run(_sta_sort)

    def apply_auto_filter(
        self,
        range_address: Optional[str] = None,
        field_index: int = 1,
        criteria1: str = "",
    ) -> Dict[str, Any]:
        """Enable or apply criteria to an Excel AutoFilter."""
        valid_range = self.validator.validate_range_address(range_address) if range_address else None

        def _sta_filter() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range) if valid_range else ws.UsedRange
            if criteria1:
                rng.AutoFilter(Field=field_index, Criteria1=criteria1)
            else:
                rng.AutoFilter()

            return {
                "status": "SUCCESS",
                "range": rng.Address,
                "field_index": field_index,
                "criteria": criteria1,
            }

        return self.worker.run(_sta_filter)

    def clear_filters(self) -> Dict[str, Any]:
        """Show all data by clearing current AutoFilter criteria."""
        def _sta_clear() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            if ws.AutoFilterMode:
                ws.ShowAllData()

            return {
                "status": "SUCCESS",
                "cleared": True,
            }

        return self.worker.run(_sta_clear)

    def remove_auto_filter(self) -> Dict[str, Any]:
        """Turn off AutoFilter dropdown arrows completely."""
        def _sta_remove_af() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            ws.AutoFilterMode = False
            return {
                "status": "SUCCESS",
                "autofilter_disabled": True,
            }

        return self.worker.run(_sta_remove_af)
