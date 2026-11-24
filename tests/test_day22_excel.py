"""
Day 22 Comprehensive Test Suite — Advanced Microsoft Excel Automation.
Tests Excel Adapter, Workbook/Worksheet Manager, Cell/Range Engines, Formula Engine,
Auditor, Formatting, Conditional Formatting, Charts, Pivots, Data Cleaner, Validation,
Page Setup, and MCP Facade.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_office.models.excel_models import (
    ExcelCalculationMode,
    ExcelChartConfig,
    ExcelChartType,
    ExcelConditionalFormattingRule,
    ExcelDataCleanConfig,
    ExcelFormatOptions,
    ExcelPivotAggregation,
    ExcelPivotConfig,
    ExcelRangeData,
    ExcelTableConfig,
    ExcelWorkbookMetadata,
    ExcelWorksheetMetadata,
)
from zye_office.excel.excel_constants import ExcelConstants
from zye_office.excel.excel_validator import ExcelValidator
from zye_office.excel.excel_permissions import ExcelPermissionEngine, ExcelRiskLevel
from zye_office.excel.excel_adapter import ExcelAdapter
from zye_office.excel.excel_formula_engine import ExcelFormulaEngine
from zye_office.excel.excel_formula_auditor import ExcelFormulaAuditor
from zye_office.excel.excel_data_cleaner import ExcelDataCleaner
from zye_office.excel.excel_formatting_engine import ExcelFormattingEngine
from zye_office.excel.excel_chart_engine import ExcelChartEngine
from zye_office.excel.excel_pivot_engine import ExcelPivotEngine
from zye_office.excel.excel_data_validation import ExcelDataValidationEngine
from zye_office.excel.excel_errors import (
    ExcelFormulaInvalidError,
    ExcelSecurityError,
)
from zye_office.integration.excel_mcp_integration import ExcelMCPIntegrationFacade


class TestDay22ExcelAutomation(unittest.TestCase):

    def setUp(self) -> None:
        self.validator = ExcelValidator()
        self.adapter = ExcelAdapter()

    def test_workbook_metadata_model(self) -> None:
        """Verify Excel workbook metadata model."""
        meta = ExcelWorkbookMetadata(
            workbook_name="Sales_Q4.xlsx",
            sheet_count=3,
            sheet_names=["Sheet1", "Summary", "Data"],
            active_sheet_name="Summary",
            is_saved=True,
        )
        self.assertEqual(meta.workbook_name, "Sales_Q4.xlsx")
        self.assertEqual(meta.sheet_count, 3)
        self.assertEqual(meta.active_sheet_name, "Summary")

    def test_excel_constants(self) -> None:
        """Verify Excel COM constants."""
        self.assertEqual(ExcelConstants.xlColumnClustered, 51)
        self.assertEqual(ExcelConstants.xlLine, 4)
        self.assertEqual(ExcelConstants.xlCalculationAutomatic, -4105)
        self.assertEqual(ExcelConstants.xlCalculationManual, -4135)

    def test_excel_formula_auditor_mock(self) -> None:
        """Verify formula auditor handles mocked worksheet formulas."""
        auditor = ExcelFormulaAuditor(adapter=self.adapter)
        mock_ws = MagicMock()
        mock_rng = MagicMock()
        mock_rng.SpecialCells.side_effect = Exception("No formulas found")
        mock_ws.UsedRange = mock_rng

        with patch.object(self.adapter, "get_active_worksheet_raw", return_value=mock_ws):
            res = auditor.audit_formula_range()
            self.assertEqual(res["status"], "SUCCESS")
            self.assertEqual(res["error_count"], 0)

    def test_excel_data_cleaner_mock(self) -> None:
        """Verify data cleaner whitespace trimming with mocked worksheet."""
        cleaner = ExcelDataCleaner(adapter=self.adapter)
        mock_ws = MagicMock()
        mock_ws.ProtectContents = False
        mock_rng = MagicMock()
        mock_rng.Value = (("  Product A  ", 100), ("Product B", "  In Stock  "))
        mock_ws.UsedRange = mock_rng

        with patch.object(self.adapter, "get_active_worksheet_raw", return_value=mock_ws):
            res = cleaner.trim_extra_spaces()
            self.assertEqual(res["status"], "SUCCESS")
            self.assertTrue(res["cells_trimmed"] > 0)

    def test_excel_validator(self) -> None:
        """Verify formula and sheet name validation."""
        self.assertEqual(self.validator.validate_formula("=SUM(A1:A10)"), "=SUM(A1:A10)")
        self.assertEqual(self.validator.validate_formula("=VLOOKUP(A1, B1:C10, 2, FALSE)"), "=VLOOKUP(A1, B1:C10, 2, FALSE)")
        self.assertEqual(self.validator.validate_worksheet_name("Sales_2026"), "Sales_2026")

        with self.assertRaises(ExcelSecurityError):
            self.validator.validate_worksheet_name("Invalid/Sheet*Name")
        with self.assertRaises(ExcelSecurityError):
            self.validator.validate_worksheet_name("a" * 32)  # Max 31 chars
        with self.assertRaises(ExcelFormulaInvalidError):
            self.validator.validate_formula("=SUM(A1:A10")  # Unbalanced parentheses

    def test_excel_permissions(self) -> None:
        """Verify Excel risk levels."""
        self.assertEqual(
            ExcelPermissionEngine.get_risk_level("excel_delete_worksheet"),
            ExcelRiskLevel.HIGH_RISK,
        )
        self.assertEqual(
            ExcelPermissionEngine.get_risk_level("excel_get_cell_value"),
            ExcelRiskLevel.READ_ONLY,
        )

    def test_excel_mcp_facade_instantiation(self) -> None:
        """Verify ExcelMCPIntegrationFacade instantiates cleanly with all sub-engines."""
        facade = ExcelMCPIntegrationFacade()
        self.assertIsNotNone(facade.adapter)
        self.assertIsNotNone(facade.workbook_manager)
        self.assertIsNotNone(facade.worksheet_manager)
        self.assertIsNotNone(facade.cell_engine)
        self.assertIsNotNone(facade.range_engine)
        self.assertIsNotNone(facade.formula_engine)
        self.assertIsNotNone(facade.formula_auditor)
        self.assertIsNotNone(facade.formatting_engine)
        self.assertIsNotNone(facade.cf_engine)
        self.assertIsNotNone(facade.chart_engine)
        self.assertIsNotNone(facade.pivot_engine)
        self.assertIsNotNone(facade.table_engine)
        self.assertIsNotNone(facade.dv_engine)
        self.assertIsNotNone(facade.data_cleaner)
        self.assertIsNotNone(facade.print_engine)


if __name__ == "__main__":
    unittest.main()
