"""
Input Validation & Constraint Enforcement for Microsoft Excel Automation — Zye Day 22.
"""

from __future__ import annotations

import re
from typing import Any, List, Optional
from zye_office.excel.excel_errors import (
    ExcelFormulaInvalidError,
    ExcelInvalidCellError,
    ExcelInvalidRangeError,
    ExcelSecurityError,
)

# Regex for single cell address (e.g. A1, AA200, $B$10)
CELL_REGEX = re.compile(r"^\$?([A-Za-z]{1,3})\$?([1-9][0-9]{0,6})$")

# Regex for range address (e.g. A1:B10, $C$5:$D$20, Sheet1!A1:C10)
RANGE_REGEX = re.compile(
    r"^(?:(?:'([^']+)'|([A-Za-z0-9_\u0B80-\u0BFF]+))!)?\$?([A-Za-z]{1,3})\$?([1-9][0-9]{0,6}):\$?([A-Za-z]{1,3})\$?([1-9][0-9]{0,6})$"
)

# Invalid characters in Excel worksheet names
FORBIDDEN_SHEET_CHARS = set(r':\/?*[]')


class ExcelValidator:
    """Validates cell coordinates, ranges, sheet names, formulas, and security boundaries."""

    @staticmethod
    def validate_cell_address(cell: str) -> str:
        """Ensure cell is a valid A1-style reference (e.g. 'A1', 'C21')."""
        if not cell or not isinstance(cell, str):
            raise ExcelInvalidCellError(str(cell))
        clean = cell.strip().replace("$", "").upper()
        if not CELL_REGEX.match(clean):
            raise ExcelInvalidCellError(cell)
        return clean

    @staticmethod
    def validate_range_address(range_str: str) -> str:
        """Ensure range is a valid A1:B2 reference (or single cell)."""
        if not range_str or not isinstance(range_str, str):
            raise ExcelInvalidRangeError(str(range_str))
        clean = range_str.strip().replace("$", "")
        if ":" not in clean:
            # Single cell passed as range
            return ExcelValidator.validate_cell_address(clean)

        match = RANGE_REGEX.match(clean)
        if not match:
            # Check if it is a whole column or whole row (e.g., A:A or 1:1)
            col_match = re.match(r"^([A-Za-z]{1,3}):([A-Za-z]{1,3})$", clean)
            row_match = re.match(r"^([1-9][0-9]{0,6}):([1-9][0-9]{0,6})$", clean)
            if not col_match and not row_match:
                raise ExcelInvalidRangeError(range_str)
        return clean

    @staticmethod
    def validate_worksheet_name(name: str) -> str:
        """Ensure worksheet name conforms to Excel limits (1-31 chars, no invalid symbols)."""
        if not name or not isinstance(name, str):
            raise ExcelSecurityError("Worksheet name cannot be empty.", "EXCEL_SHEET_NAME_INVALID")
        clean = name.strip()
        if len(clean) == 0 or len(clean) > 31:
            raise ExcelSecurityError(
                f"Worksheet name '{clean}' length ({len(clean)}) exceeds Excel limit of 1 to 31 characters.",
                "EXCEL_SHEET_NAME_INVALID",
            )
        if any(c in FORBIDDEN_SHEET_CHARS for c in clean):
            raise ExcelSecurityError(
                f"Worksheet name '{clean}' contains invalid characters (cannot include : \\ / ? * [ ]).",
                "EXCEL_SHEET_NAME_INVALID",
            )
        return clean

    @staticmethod
    def validate_formula(formula: str, allow_external: bool = False) -> str:
        """Ensure formula syntax is valid and free of dangerous injection vectors."""
        if not formula or not isinstance(formula, str):
            raise ExcelFormulaInvalidError(str(formula), "Formula string cannot be empty")
        clean = formula.strip()
        if not clean.startswith("="):
            clean = "=" + clean

        if len(clean) > 8192:
            raise ExcelFormulaInvalidError(clean, "Formula length exceeds maximum of 8,192 characters")

        # Parenthesis balance
        if clean.count("(") != clean.count(")"):
            raise ExcelFormulaInvalidError(clean, "Unmatched parentheses in formula")

        # Check for dangerous DDE / command injection patterns
        upper = clean.upper()
        dangerous_tokens = ["EXEC(", "CMD|", "MSEXCEL|", "POWERSHELL|", "APPLICATION.RUN"]
        for token in dangerous_tokens:
            if token in upper:
                raise ExcelSecurityError(
                    f"Blocked potentially malicious token '{token}' in formula.",
                    "EXCEL_UNSAFE_FORMULA_BLOCKED",
                )

        if not allow_external:
            # Check for external workbook brackets '[workbook.xlsx]'
            if "[" in clean and "]" in clean:
                raise ExcelSecurityError(
                    "External workbook links in formulas are disabled by default policy.",
                    "EXCEL_EXTERNAL_LINK_BLOCKED",
                )

        return clean

    @staticmethod
    def sanitize_csv_field(val: Any) -> str:
        """Neutralize potential CSV/Spreadsheet formula injection."""
        text = str(val or "")
        if text.startswith(("=", "+", "-", "@", "\t", "\r")):
            return "'" + text
        return text
