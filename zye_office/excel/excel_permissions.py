"""
Permission Engine & Safety Risk Classifier for Excel Automation — Zye Day 22.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from zye_office.excel.excel_errors import ExcelSecurityError


class ExcelRiskLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"


class ExcelPermissionEngine:
    """Classifies risk levels and enforces user confirmation for destructive Excel operations."""

    RISK_MAP = {
        # Read-only
        "excel_inspect_workbook": ExcelRiskLevel.READ_ONLY,
        "excel_get_worksheets": ExcelRiskLevel.READ_ONLY,
        "excel_get_cell_value": ExcelRiskLevel.READ_ONLY,
        "excel_get_cell_formula": ExcelRiskLevel.READ_ONLY,
        "excel_get_range_values": ExcelRiskLevel.READ_ONLY,
        "excel_audit_formulas": ExcelRiskLevel.READ_ONLY,
        "excel_find_formula_errors": ExcelRiskLevel.READ_ONLY,
        "excel_get_charts": ExcelRiskLevel.READ_ONLY,
        "excel_get_pivot_tables": ExcelRiskLevel.READ_ONLY,
        "excel_get_tables": ExcelRiskLevel.READ_ONLY,
        "excel_inspect_data_validation": ExcelRiskLevel.READ_ONLY,
        "excel_get_named_ranges": ExcelRiskLevel.READ_ONLY,
        "excel_analyze_dataset": ExcelRiskLevel.READ_ONLY,
        "excel_summarize_dataset": ExcelRiskLevel.READ_ONLY,
        "excel_generate_data_insights": ExcelRiskLevel.READ_ONLY,
        "excel_export_pdf": ExcelRiskLevel.READ_ONLY,

        # Low Risk
        "excel_set_cell_value": ExcelRiskLevel.LOW_RISK,
        "excel_set_cell_formula": ExcelRiskLevel.LOW_RISK,
        "excel_fill_formula_down": ExcelRiskLevel.LOW_RISK,
        "excel_format_range": ExcelRiskLevel.LOW_RISK,
        "excel_autofit_columns": ExcelRiskLevel.LOW_RISK,
        "excel_set_number_format": ExcelRiskLevel.LOW_RISK,
        "excel_create_named_range": ExcelRiskLevel.LOW_RISK,
        "excel_save_workbook": ExcelRiskLevel.LOW_RISK,

        # Medium Risk
        "excel_create_workbook": ExcelRiskLevel.MEDIUM_RISK,
        "excel_create_worksheet": ExcelRiskLevel.MEDIUM_RISK,
        "excel_rename_worksheet": ExcelRiskLevel.MEDIUM_RISK,
        "excel_duplicate_worksheet": ExcelRiskLevel.MEDIUM_RISK,
        "excel_set_range_values": ExcelRiskLevel.MEDIUM_RISK,
        "excel_add_conditional_formatting": ExcelRiskLevel.MEDIUM_RISK,
        "excel_create_chart": ExcelRiskLevel.MEDIUM_RISK,
        "excel_update_chart": ExcelRiskLevel.MEDIUM_RISK,
        "excel_create_pivot_table": ExcelRiskLevel.MEDIUM_RISK,
        "excel_refresh_pivot_table": ExcelRiskLevel.MEDIUM_RISK,
        "excel_create_pivot_chart": ExcelRiskLevel.MEDIUM_RISK,
        "excel_create_table": ExcelRiskLevel.MEDIUM_RISK,
        "excel_format_table": ExcelRiskLevel.MEDIUM_RISK,
        "excel_add_dropdown_validation": ExcelRiskLevel.MEDIUM_RISK,
        "excel_add_data_validation": ExcelRiskLevel.MEDIUM_RISK,
        "excel_sort_range": ExcelRiskLevel.MEDIUM_RISK,
        "excel_apply_filter": ExcelRiskLevel.MEDIUM_RISK,
        "excel_clear_filters": ExcelRiskLevel.MEDIUM_RISK,
        "excel_generate_report": ExcelRiskLevel.MEDIUM_RISK,
        "excel_generate_kpi_dashboard": ExcelRiskLevel.MEDIUM_RISK,

        # High Risk (Requires Confirmation)
        "excel_delete_worksheet": ExcelRiskLevel.HIGH_RISK,
        "excel_delete_chart": ExcelRiskLevel.HIGH_RISK,
        "excel_delete_named_range": ExcelRiskLevel.HIGH_RISK,
        "excel_remove_conditional_formatting": ExcelRiskLevel.HIGH_RISK,
        "excel_remove_duplicates": ExcelRiskLevel.HIGH_RISK,
        "excel_clear_range_contents": ExcelRiskLevel.HIGH_RISK,
        "excel_delete_rows": ExcelRiskLevel.HIGH_RISK,
        "excel_delete_columns": ExcelRiskLevel.HIGH_RISK,
    }

    @classmethod
    def get_risk_level(cls, operation_name: str) -> ExcelRiskLevel:
        return cls.RISK_MAP.get(operation_name, ExcelRiskLevel.MEDIUM_RISK)

    @classmethod
    def requires_confirmation(cls, operation_name: str) -> bool:
        return cls.get_risk_level(operation_name) in (ExcelRiskLevel.HIGH_RISK, ExcelRiskLevel.CRITICAL)

    @classmethod
    def enforce_confirmation(cls, operation_name: str, confirmed: bool) -> None:
        if cls.requires_confirmation(operation_name) and not confirmed:
            raise ExcelSecurityError(
                f"Destructive operation '{operation_name}' requires explicit user confirmation.",
                error_code="EXCEL_CONFIRMATION_REQUIRED",
            )
