"""
Structured Error Taxonomy for Microsoft Excel Automation — Zye Day 22.
Provides dedicated exception classes and remediation advice for Excel operations.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from zye_office.errors import ZyeOfficeError


class ExcelAutomationError(ZyeOfficeError):
    """Base exception for all Microsoft Excel automation errors."""
    def __init__(
        self,
        message: str,
        error_code: str = "EXCEL_AUTOMATION_ERROR",
        remediation: str = "Ensure Microsoft Excel is installed, running, and accessible.",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            code=error_code,
            message=message,
            app_name="excel",
            remediation=remediation,
            details=details,
        )


class ExcelNotInstalledError(ExcelAutomationError):
    def __init__(self, message: str = "Microsoft Excel is not installed or registered on this system.") -> None:
        super().__init__(
            message=message,
            error_code="EXCEL_NOT_INSTALLED",
            remediation="Install Microsoft Office 2016+ or Microsoft 365 on this Windows computer.",
        )


class ExcelCOMUnavailableError(ExcelAutomationError):
    def __init__(self, message: str = "Failed to establish COM connection to Excel.Application.") -> None:
        super().__init__(
            message=message,
            error_code="EXCEL_COM_UNAVAILABLE",
            remediation="Restart Microsoft Excel or terminate orphaned EXCEL.EXE processes.",
        )


class ExcelNoActiveWorkbookError(ExcelAutomationError):
    def __init__(self, message: str = "Excel is open, but no active workbook is available.") -> None:
        super().__init__(
            message=message,
            error_code="EXCEL_NO_ACTIVE_WORKBOOK",
            remediation="Open an existing workbook or create a new workbook first.",
        )


class ExcelNoActiveWorksheetError(ExcelAutomationError):
    def __init__(self, message: str = "No active worksheet found in the current workbook.") -> None:
        super().__init__(
            message=message,
            error_code="EXCEL_NO_ACTIVE_WORKSHEET",
            remediation="Ensure the workbook contains at least one visible worksheet.",
        )


class ExcelWorkbookReadOnlyError(ExcelAutomationError):
    def __init__(self, message: str = "Target workbook is opened in read-only mode.") -> None:
        super().__init__(
            message=message,
            error_code="EXCEL_WORKBOOK_READ_ONLY",
            remediation="Save the workbook under a different file name using save_as.",
        )


class ExcelWorkbookProtectedError(ExcelAutomationError):
    def __init__(self, message: str = "Workbook structure is password-protected or locked.") -> None:
        super().__init__(
            message=message,
            error_code="EXCEL_WORKBOOK_PROTECTED",
            remediation="Unprotect the workbook manually in Excel before executing structural modifications.",
        )


class ExcelSheetProtectedError(ExcelAutomationError):
    def __init__(self, message: str = "Worksheet is protected against modifications.") -> None:
        super().__init__(
            message=message,
            error_code="EXCEL_SHEET_PROTECTED",
            remediation="Unprotect the sheet or specify a valid password to modify its cells.",
        )


class ExcelSheetNotFoundError(ExcelAutomationError):
    def __init__(self, sheet_name: str) -> None:
        super().__init__(
            message=f"Worksheet '{sheet_name}' was not found in active workbook.",
            error_code="EXCEL_SHEET_NOT_FOUND",
            remediation="Inspect available worksheets with excel_get_worksheets() to verify the sheet name.",
            details={"requested_sheet": sheet_name},
        )


class ExcelInvalidCellError(ExcelAutomationError):
    def __init__(self, cell_reference: str) -> None:
        super().__init__(
            message=f"Cell reference '{cell_reference}' is not a valid Excel A1 address.",
            error_code="EXCEL_INVALID_CELL",
            remediation="Provide standard A1 reference notation such as 'A1', 'C21', or 'AA100'.",
            details={"cell": cell_reference},
        )


class ExcelInvalidRangeError(ExcelAutomationError):
    def __init__(self, range_reference: str) -> None:
        super().__init__(
            message=f"Range reference '{range_reference}' is invalid or out of bounds.",
            error_code="EXCEL_INVALID_RANGE",
            remediation="Provide standard range address notation such as 'A1:C20' or 'Sheet1!A1:B10'.",
            details={"range": range_reference},
        )


class ExcelFormulaInvalidError(ExcelAutomationError):
    def __init__(self, formula: str, reason: str = "Syntax error or unsafe construct") -> None:
        super().__init__(
            message=f"Formula '{formula}' is invalid: {reason}.",
            error_code="EXCEL_FORMULA_INVALID",
            remediation="Verify formula syntax, matching parentheses, and supported function names.",
            details={"formula": formula, "reason": reason},
        )


class ExcelFormulaResultError(ExcelAutomationError):
    def __init__(self, cell: str, error_value: str) -> None:
        super().__init__(
            message=f"Formula at {cell} evaluated to Excel error: {error_value}.",
            error_code="EXCEL_FORMULA_RESULT_ERROR",
            remediation="Check precedent cells for divide-by-zero, missing lookups, or type mismatches.",
            details={"cell": cell, "error_value": error_value},
        )


class ExcelChartError(ExcelAutomationError):
    def __init__(self, message: str, error_code: str = "EXCEL_CHART_CREATION_FAILED") -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            remediation="Verify source data range contains headers and numeric values for chart plotting.",
        )


class ExcelPivotError(ExcelAutomationError):
    def __init__(self, message: str, error_code: str = "EXCEL_PIVOT_CREATION_FAILED") -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            remediation="Ensure source table has unambiguous header titles and non-empty column names.",
        )


class ExcelDataValidationError(ExcelAutomationError):
    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            error_code="EXCEL_DATA_VALIDATION_FAILED",
            remediation="Verify validation criteria, range bounds, and input formats.",
        )


class ExcelSecurityError(ExcelAutomationError):
    def __init__(self, message: str, error_code: str = "EXCEL_SECURITY_VIOLATION") -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            remediation="Operation was rejected because it violates Zye AI security and safe execution policies.",
        )
