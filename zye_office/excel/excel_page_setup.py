"""
Page Setup & Layout Engine for Microsoft Excel — Zye Day 22.
Configures print areas, orientations, paper sizes, margins, headers, and fit-to-page scaling.
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
from zye_office.models.excel_models import ExcelPageSetupConfig

logger = logging.getLogger("zye.office.excel.page_setup")

ORIENT_MAP = {
    "portrait": ExcelConstants.xlPortrait,
    "landscape": ExcelConstants.xlLandscape,
}

PAPER_MAP = {
    "a4": ExcelConstants.xlPaperA4,
    "letter": ExcelConstants.xlPaperLetter,
    "legal": ExcelConstants.xlPaperLegal,
    "a3": ExcelConstants.xlPaperA3,
}


class ExcelPageSetupEngine:
    """Manages Excel PageSetup properties for printing and PDF generation."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        validator: Optional[ExcelValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or ExcelValidator()

    def set_print_area(self, range_address: str) -> Dict[str, Any]:
        """Set specific print area for active worksheet."""
        valid_range = self.validator.validate_range_address(range_address)

        def _sta_set_pa() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            ws.PageSetup.PrintArea = valid_range
            return {
                "status": "SUCCESS",
                "sheet_name": ws.Name,
                "print_area": valid_range,
            }

        return self.worker.run(_sta_set_pa)

    def clear_print_area(self) -> Dict[str, Any]:
        """Clear print area to print entire used worksheet."""
        def _sta_clear_pa() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            ws.PageSetup.PrintArea = ""
            return {
                "status": "SUCCESS",
                "print_area_cleared": True,
            }

        return self.worker.run(_sta_clear_pa)

    def configure_page_setup(
        self,
        config: Union[ExcelPageSetupConfig, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Configure orientation, paper size, margins, and page fitting."""
        if isinstance(config, dict):
            cfg = ExcelPageSetupConfig(**config)
        else:
            cfg = config

        orient_val = ORIENT_MAP.get(cfg.orientation.lower(), ExcelConstants.xlPortrait)
        paper_val = PAPER_MAP.get(cfg.paper_size.lower(), ExcelConstants.xlPaperA4)

        def _sta_setup() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            ps = ws.PageSetup
            ps.Orientation = orient_val
            ps.PaperSize = paper_val

            if cfg.print_area:
                ps.PrintArea = self.validator.validate_range_address(cfg.print_area)

            # Margins (points)
            if cfg.top_margin_points:
                ps.TopMargin = cfg.top_margin_points
            if cfg.bottom_margin_points:
                ps.BottomMargin = cfg.bottom_margin_points
            if cfg.left_margin_points:
                ps.LeftMargin = cfg.left_margin_points
            if cfg.right_margin_points:
                ps.RightMargin = cfg.right_margin_points

            # Fit to page
            if cfg.fit_to_page_wide is not None:
                ps.Zoom = False
                ps.FitToPagesWide = cfg.fit_to_page_wide
                ps.FitToPagesTall = cfg.fit_to_page_tall or False

            # Repeat header rows
            if cfg.repeat_header_rows:
                ps.PrintTitleRows = cfg.repeat_header_rows

            return {
                "status": "SUCCESS",
                "orientation": cfg.orientation,
                "paper_size": cfg.paper_size,
                "sheet_name": ws.Name,
            }

        return self.worker.run(_sta_setup)
