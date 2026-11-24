"""
Data Validation Engine for Microsoft Excel — Zye Day 22.
Adds dropdown lists, numeric bounds, date constraints, and custom input/error alerts.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union
from zye_office.excel.excel_adapter import ExcelAdapter
from zye_office.excel.excel_constants import ExcelConstants
from zye_office.excel.excel_errors import (
    ExcelDataValidationError,
    ExcelNoActiveWorksheetError,
    ExcelSheetProtectedError,
)
from zye_office.excel.excel_validator import ExcelValidator
from zye_office.models.excel_models import ExcelDataValidationConfig

logger = logging.getLogger("zye.office.excel.data_validation")

DV_TYPE_MAP = {
    "list": ExcelConstants.xlValidateList,
    "whole": ExcelConstants.xlValidateWholeNumber,
    "decimal": ExcelConstants.xlValidateDecimal,
    "date": ExcelConstants.xlValidateDate,
    "text_length": ExcelConstants.xlValidateTextLength,
    "custom": ExcelConstants.xlValidateCustom,
}

ALERT_STYLE_MAP = {
    "stop": ExcelConstants.xlValidAlertStop,
    "warning": ExcelConstants.xlValidAlertWarning,
    "information": ExcelConstants.xlValidAlertInformation,
}


class ExcelDataValidationEngine:
    """Manages Excel Validation objects on cell ranges."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        validator: Optional[ExcelValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or ExcelValidator()

    def add_dropdown_validation(
        self,
        range_address: str,
        values: List[str],
        allow_blank: bool = True,
        error_title: str = "Invalid Selection",
        error_message: str = "Please select an item from the authorized dropdown list.",
    ) -> Dict[str, Any]:
        """Add a simple dropdown list validation rule."""
        valid_range = self.validator.validate_range_address(range_address)
        if not values:
            raise ExcelDataValidationError("Dropdown list requires at least one item.")

        list_formula = ",".join(str(v).strip() for v in values)

        def _sta_add_dropdown() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range)
            rng.Validation.Delete()
            rng.Validation.Add(
                Type=ExcelConstants.xlValidateList,
                AlertStyle=ExcelConstants.xlValidAlertStop,
                Operator=ExcelConstants.xlBetween,
                Formula1=list_formula,
            )
            rng.Validation.IgnoreBlank = allow_blank
            rng.Validation.InCellDropdown = True
            rng.Validation.ShowError = True
            rng.Validation.ErrorTitle = error_title
            rng.Validation.ErrorMessage = error_message

            return {
                "status": "SUCCESS",
                "range": valid_range,
                "type": "DROPDOWN_LIST",
                "values": values,
            }

        return self.worker.run(_sta_add_dropdown)

    def add_data_validation(
        self,
        range_address: str,
        config: Union[ExcelDataValidationConfig, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Add arbitrary data validation rule (numeric, date, text length, custom)."""
        valid_range = self.validator.validate_range_address(range_address)
        if isinstance(config, dict):
            cfg = ExcelDataValidationConfig(**config)
        else:
            cfg = config

        dv_type = DV_TYPE_MAP.get(cfg.validation_type.lower(), ExcelConstants.xlValidateWholeNumber)
        alert_style = ALERT_STYLE_MAP.get(cfg.error_style.lower(), ExcelConstants.xlValidAlertStop)

        def _sta_add_dv() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            rng = ws.Range(valid_range)
            rng.Validation.Delete()
            rng.Validation.Add(
                Type=dv_type,
                AlertStyle=alert_style,
                Operator=ExcelConstants.xlBetween,
                Formula1=str(cfg.formula1),
                Formula2=str(cfg.formula2) if cfg.formula2 else None,
            )
            rng.Validation.IgnoreBlank = cfg.allow_blank

            if cfg.show_input_message and cfg.input_message:
                rng.Validation.ShowInput = True
                rng.Validation.InputTitle = cfg.input_title or "Notice"
                rng.Validation.InputMessage = cfg.input_message

            if cfg.show_error_message and cfg.error_message:
                rng.Validation.ShowError = True
                rng.Validation.ErrorTitle = cfg.error_title or "Error"
                rng.Validation.ErrorMessage = cfg.error_message

            return {
                "status": "SUCCESS",
                "range": valid_range,
                "validation_type": cfg.validation_type,
                "formula1": cfg.formula1,
                "formula2": cfg.formula2,
            }

        return self.worker.run(_sta_add_dv)

    def remove_data_validation(self, range_address: str) -> Dict[str, Any]:
        """Clear validation rules from specified range."""
        valid_range = self.validator.validate_range_address(range_address)

        def _sta_del_dv() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            ws.Range(valid_range).Validation.Delete()
            return {
                "status": "SUCCESS",
                "range": valid_range,
                "cleared": True,
            }

        return self.worker.run(_sta_del_dv)

    def inspect_data_validation(self, range_address: str) -> Dict[str, Any]:
        """Check if range has data validation configured."""
        valid_range = self.validator.validate_range_address(range_address)

        def _sta_inspect_dv() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            c = ws.Range(valid_range).Cells(1, 1)
            has_val = False
            v_type = None
            f1 = None
            f2 = None
            try:
                v = c.Validation
                v_type = getattr(v, "Type", None)
                f1 = getattr(v, "Formula1", None)
                f2 = getattr(v, "Formula2", None)
                has_val = v_type is not None
            except Exception:
                pass

            return {
                "status": "SUCCESS",
                "cell": valid_range,
                "has_validation": has_val,
                "type": v_type,
                "formula1": f1,
                "formula2": f2,
            }

        return self.worker.run(_sta_inspect_dv)
