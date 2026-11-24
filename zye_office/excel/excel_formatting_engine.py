"""
Advanced Formatting & Styling Engine for Microsoft Excel — Zye Day 22.
Applies typography, fills, borders, alignments, number formatting, and corporate presets.
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
from zye_office.models.excel_models import ExcelFormatOptions

logger = logging.getLogger("zye.office.excel.formatting")

ALIGN_MAP = {
    "left": ExcelConstants.xlHAlignLeft,
    "center": ExcelConstants.xlHAlignCenter,
    "right": ExcelConstants.xlHAlignRight,
    "justify": ExcelConstants.xlHAlignJustify,
}

VALIGN_MAP = {
    "top": ExcelConstants.xlVAlignTop,
    "center": ExcelConstants.xlVAlignCenter,
    "bottom": ExcelConstants.xlVAlignBottom,
}


class ExcelFormattingEngine:
    """Manages cell styling, alignments, borders, number formats, and corporate presets."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        validator: Optional[ExcelValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or ExcelValidator()

    def format_range(
        self,
        range_address: str,
        options: Union[ExcelFormatOptions, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Apply typography, borders, alignments, and number formatting to a range."""
        valid_range = self.validator.validate_range_address(range_address)
        if isinstance(options, dict):
            opts = ExcelFormatOptions(**options)
        else:
            opts = options

        def _sta_format() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range)

            # Font attributes
            if opts.font_name:
                rng.Font.Name = opts.font_name
            if opts.font_size:
                rng.Font.Size = opts.font_size
            if opts.bold is not None:
                rng.Font.Bold = opts.bold
            if opts.italic is not None:
                rng.Font.Italic = opts.italic
            if opts.underline is not None:
                rng.Font.Underline = 2 if opts.underline else -4142
            if opts.color is not None:
                rng.Font.Color = opts.color

            # Fill / Interior Background
            if opts.bg_color is not None:
                rng.Interior.Color = opts.bg_color

            # Alignment
            if opts.horizontal_alignment:
                h_val = ALIGN_MAP.get(opts.horizontal_alignment.lower())
                if h_val:
                    rng.HorizontalAlignment = h_val
            if opts.vertical_alignment:
                v_val = VALIGN_MAP.get(opts.vertical_alignment.lower())
                if v_val:
                    rng.VerticalAlignment = v_val

            # Number Format
            if opts.number_format:
                rng.NumberFormat = opts.number_format

            # Text wrap
            if opts.wrap_text is not None:
                rng.WrapText = opts.wrap_text

            # Dimensions
            if opts.row_height:
                rng.RowHeight = opts.row_height
            if opts.column_width:
                rng.ColumnWidth = opts.column_width

            # Merge and center
            if opts.merge_and_center:
                rng.Merge()
                rng.HorizontalAlignment = ExcelConstants.xlHAlignCenter

            # Borders
            if opts.borders:
                self._apply_borders(rng, opts.borders)

            return {
                "status": "SUCCESS",
                "range": valid_range,
                "applied_options": opts.model_dump(exclude_none=True),
            }

        return self.worker.run(_sta_format)

    def autofit_columns(self, range_address: Optional[str] = None) -> Dict[str, Any]:
        """Autofit column widths to content."""
        valid_range = self.validator.validate_range_address(range_address) if range_address else None

        def _sta_autofit() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            rng = ws.Range(valid_range) if valid_range else ws.UsedRange
            rng.Columns.AutoFit()
            return {
                "status": "SUCCESS",
                "range": rng.Address,
                "autofit_columns": True,
            }

        return self.worker.run(_sta_autofit)

    def set_number_format(self, range_address: str, number_format: str) -> Dict[str, Any]:
        """Set specific number format string (e.g. '$#,##0.00', '0.0%', 'YYYY-MM-DD')."""
        valid_range = self.validator.validate_range_address(range_address)

        def _sta_num_fmt() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range)
            rng.NumberFormat = number_format
            return {
                "status": "SUCCESS",
                "range": valid_range,
                "number_format": number_format,
            }

        return self.worker.run(_sta_num_fmt)

    def apply_preset(self, range_address: str, preset_name: str) -> Dict[str, Any]:
        """Apply standard corporate formatting preset (e.g. BUSINESS_REPORT, FINANCIAL_REPORT)."""
        valid_range = self.validator.validate_range_address(range_address)
        norm_preset = preset_name.upper().strip()

        preset_configs = {
            "BUSINESS_REPORT": ExcelFormatOptions(
                font_name="Calibri",
                font_size=11.0,
                borders="thin",
                horizontal_alignment="left",
            ),
            "FINANCIAL_REPORT": ExcelFormatOptions(
                font_name="Calibri",
                font_size=10.0,
                number_format="#,##0.00",
                borders="thin",
                horizontal_alignment="right",
            ),
            "KPI_DASHBOARD": ExcelFormatOptions(
                font_name="Segoe UI",
                font_size=11.0,
                bold=True,
                horizontal_alignment="center",
            ),
            "EXECUTIVE_SUMMARY": ExcelFormatOptions(
                font_name="Arial",
                font_size=12.0,
                bold=True,
                color=16711680,  # Deep Blue
                horizontal_alignment="left",
            ),
        }

        opts = preset_configs.get(norm_preset, preset_configs["BUSINESS_REPORT"])
        return self.format_range(valid_range, opts)

    def _apply_borders(self, rng: Any, border_style: str) -> None:
        """Apply border lines to range."""
        style = border_style.lower().strip()
        weight = ExcelConstants.xlThin
        if style == "thick":
            weight = ExcelConstants.xlThick
        elif style == "medium":
            weight = ExcelConstants.xlMedium

        for edge in (
            ExcelConstants.xlEdgeLeft,
            ExcelConstants.xlEdgeTop,
            ExcelConstants.xlEdgeBottom,
            ExcelConstants.xlEdgeRight,
            ExcelConstants.xlInsideVertical,
            ExcelConstants.xlInsideHorizontal,
        ):
            try:
                b = rng.Borders(edge)
                b.LineStyle = ExcelConstants.xlContinuous
                b.Weight = weight
            except Exception:
                pass
