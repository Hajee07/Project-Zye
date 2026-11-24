"""
Excel MCP Tool Integration Facade — Zye Day 22.
Consolidates all modular Excel engines and coordinates validation, execution, and error formatting.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union
from zye_office.excel import (
    ExcelAdapter,
    ExcelCalculationEngine,
    ExcelCellEngine,
    ExcelChartEngine,
    ExcelConditionalFormattingEngine,
    ExcelDataCleaner,
    ExcelDataValidationEngine,
    ExcelFormattingEngine,
    ExcelFormulaAuditor,
    ExcelFormulaEngine,
    ExcelNamedRangeEngine,
    ExcelPageSetupEngine,
    ExcelPermissionEngine,
    ExcelPivotEngine,
    ExcelPrintEngine,
    ExcelRangeEngine,
    ExcelReportEngine,
    ExcelSortFilterEngine,
    ExcelTableEngine,
    ExcelValidator,
    ExcelWorkbookManager,
    ExcelWorksheetManager,
)
from zye_office.models.excel_models import (
    ExcelChartConfig,
    ExcelDataCleanConfig,
    ExcelDataValidationConfig,
    ExcelFormatOptions,
    ExcelPivotConfig,
    ExcelReportConfig,
    ExcelSortConfig,
)

logger = logging.getLogger("zye.office.excel.mcp_facade")


class ExcelMCPIntegrationFacade:
    """Consolidated facade managing all Excel automation capabilities."""

    def __init__(self) -> None:
        self.adapter = ExcelAdapter()
        self.validator = ExcelValidator()
        self.workbook_manager = ExcelWorkbookManager(adapter=self.adapter)
        self.worksheet_manager = ExcelWorksheetManager(adapter=self.adapter, validator=self.validator)
        self.range_engine = ExcelRangeEngine(adapter=self.adapter, validator=self.validator)
        self.cell_engine = ExcelCellEngine(adapter=self.adapter, validator=self.validator)
        self.formula_engine = ExcelFormulaEngine(adapter=self.adapter, validator=self.validator)
        self.formula_auditor = ExcelFormulaAuditor(adapter=self.adapter, validator=self.validator)
        self.formatting_engine = ExcelFormattingEngine(adapter=self.adapter, validator=self.validator)
        self.cf_engine = ExcelConditionalFormattingEngine(adapter=self.adapter, validator=self.validator)
        self.chart_engine = ExcelChartEngine(adapter=self.adapter, validator=self.validator)
        self.pivot_engine = ExcelPivotEngine(adapter=self.adapter, validator=self.validator)
        self.table_engine = ExcelTableEngine(adapter=self.adapter, validator=self.validator)
        self.dv_engine = ExcelDataValidationEngine(adapter=self.adapter, validator=self.validator)
        self.sort_filter_engine = ExcelSortFilterEngine(adapter=self.adapter, validator=self.validator)
        self.named_range_engine = ExcelNamedRangeEngine(adapter=self.adapter, validator=self.validator)
        self.data_cleaner = ExcelDataCleaner(adapter=self.adapter, validator=self.validator)
        self.calc_engine = ExcelCalculationEngine(adapter=self.adapter, validator=self.validator)
        self.report_engine = ExcelReportEngine(
            adapter=self.adapter,
            worksheet_manager=self.worksheet_manager,
            range_engine=self.range_engine,
            formatting_engine=self.formatting_engine,
            chart_engine=self.chart_engine,
            cf_engine=self.cf_engine,
            validator=self.validator,
        )
        self.page_setup_engine = ExcelPageSetupEngine(adapter=self.adapter, validator=self.validator)
        self.print_engine = ExcelPrintEngine(adapter=self.adapter)

    # -------------------------------------------------------------------------
    # Workbook Management
    # -------------------------------------------------------------------------

    def create_workbook(self) -> Dict[str, Any]:
        return self.workbook_manager.create_workbook()

    def open_workbook(self, file_path: str, read_only: bool = False) -> Dict[str, Any]:
        return self.workbook_manager.open_workbook(file_path=file_path, read_only=read_only)

    def inspect_workbook(self) -> Dict[str, Any]:
        return self.adapter.inspect_excel_application()

    def save_workbook(self) -> Dict[str, Any]:
        return self.workbook_manager.save_workbook()

    def save_workbook_as(self, file_path: str, overwrite: bool = False) -> Dict[str, Any]:
        return self.workbook_manager.save_workbook_as(file_path=file_path, overwrite=overwrite)

    def get_workbook_metadata(self) -> Dict[str, Any]:
        return self.workbook_manager.get_active_workbook_metadata()

    # -------------------------------------------------------------------------
    # Worksheet Management
    # -------------------------------------------------------------------------

    def get_worksheets(self) -> List[Dict[str, Any]]:
        return self.worksheet_manager.get_all_worksheets()

    def create_worksheet(self, name: Optional[str] = None) -> Dict[str, Any]:
        return self.worksheet_manager.create_worksheet(name=name)

    def rename_worksheet(self, old_name: str, new_name: str) -> Dict[str, Any]:
        return self.worksheet_manager.rename_worksheet(old_name=old_name, new_name=new_name)

    def delete_worksheet(self, name: str, confirmed: bool = False) -> Dict[str, Any]:
        return self.worksheet_manager.delete_worksheet(name=name, confirmed=confirmed)

    def duplicate_worksheet(self, name: str, new_name: Optional[str] = None) -> Dict[str, Any]:
        return self.worksheet_manager.duplicate_worksheet(name=name, new_name=new_name)

    # -------------------------------------------------------------------------
    # Cell & Range Operations
    # -------------------------------------------------------------------------

    def get_cell_value(self, cell: str) -> Dict[str, Any]:
        return self.cell_engine.get_cell_value(cell_reference=cell)

    def set_cell_value(self, cell: str, value: Any) -> Dict[str, Any]:
        return self.cell_engine.set_cell_value(cell_reference=cell, value=value)

    def get_cell_formula(self, cell: str) -> Dict[str, Any]:
        return self.cell_engine.get_cell_formula(cell_reference=cell)

    def set_cell_formula(self, cell: str, formula: str) -> Dict[str, Any]:
        return self.cell_engine.set_cell_formula(cell_reference=cell, formula=formula)

    def get_range_values(self, range_address: str) -> Dict[str, Any]:
        return self.range_engine.get_range_values(range_reference=range_address)

    def set_range_values(self, range_address: str, data: List[List[Any]]) -> Dict[str, Any]:
        return self.range_engine.set_range_values(range_reference=range_address, data=data)

    def clear_range(self, range_address: str) -> Dict[str, Any]:
        return self.range_engine.clear_range_contents(range_reference=range_address)

    # -------------------------------------------------------------------------
    # Formula Engine & Auditing
    # -------------------------------------------------------------------------

    def fill_formula_down(self, range_address: str, formula: Optional[str] = None) -> Dict[str, Any]:
        if formula:
            # Set formula on top cell first, then fill down
            top_cell = range_address.split(":")[0] if ":" in range_address else range_address
            self.cell_engine.set_cell_formula(top_cell, formula)
        return self.formula_engine.fill_formula_down(range_address=range_address)

    def audit_formulas(self, range_address: Optional[str] = None) -> Dict[str, Any]:
        return self.formula_auditor.audit_formula_range(range_address=range_address)

    def find_formula_errors(self, range_address: Optional[str] = None) -> Dict[str, Any]:
        return self.formula_auditor.find_formula_errors(range_address=range_address)

    # -------------------------------------------------------------------------
    # Formatting
    # -------------------------------------------------------------------------

    def format_range(self, range_address: str, format_options: Dict[str, Any]) -> Dict[str, Any]:
        return self.formatting_engine.format_range(range_address=range_address, options=format_options)

    def autofit_columns(self, range_address: Optional[str] = None) -> Dict[str, Any]:
        return self.formatting_engine.autofit_columns(range_address=range_address)

    def set_number_format(self, range_address: str, number_format: str) -> Dict[str, Any]:
        return self.formatting_engine.set_number_format(range_address=range_address, number_format=number_format)

    # -------------------------------------------------------------------------
    # Conditional Formatting
    # -------------------------------------------------------------------------

    def add_conditional_formatting(
        self,
        range_address: str,
        rule_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        rtype = rule_config.get("rule_type", "cell_value").lower()
        if rtype == "cell_value":
            return self.cf_engine.add_cell_value_rule(
                range_address=range_address,
                operator=rule_config.get("operator", "greater_than"),
                formula1=str(rule_config.get("formula1", "0")),
                formula2=rule_config.get("formula2"),
                font_color=rule_config.get("font_color"),
                bg_color=rule_config.get("bg_color"),
            )
        elif rtype == "formula":
            return self.cf_engine.add_formula_rule(
                range_address=range_address,
                formula=rule_config.get("formula", ""),
                font_color=rule_config.get("font_color"),
                bg_color=rule_config.get("bg_color"),
            )
        elif rtype == "duplicate":
            return self.cf_engine.add_duplicate_value_rule(
                range_address=range_address,
                font_color=rule_config.get("font_color"),
                bg_color=rule_config.get("bg_color"),
            )
        elif rtype == "color_scale":
            return self.cf_engine.add_color_scale_rule(range_address=range_address)
        elif rtype == "data_bar":
            return self.cf_engine.add_data_bar_rule(
                range_address=range_address,
                color_bgr=rule_config.get("color", 16751001),
            )
        else:
            return self.cf_engine.add_cell_value_rule(
                range_address=range_address,
                operator="greater_than",
                formula1="0",
            )

    def get_conditional_formatting(self, range_address: Optional[str] = None) -> Dict[str, Any]:
        return self.cf_engine.get_conditional_formatting_rules(range_address=range_address)

    def remove_conditional_formatting(self, range_address: Optional[str] = None) -> Dict[str, Any]:
        return self.cf_engine.remove_conditional_formatting(range_address=range_address)

    # -------------------------------------------------------------------------
    # Charts
    # -------------------------------------------------------------------------

    def create_chart(self, chart_config: Dict[str, Any]) -> Dict[str, Any]:
        return self.chart_engine.create_chart(config=chart_config)

    def get_charts(self) -> Dict[str, Any]:
        return self.chart_engine.get_charts()

    def delete_chart(self, chart_id: Union[int, str]) -> Dict[str, Any]:
        return self.chart_engine.delete_chart(chart_id=chart_id)

    # -------------------------------------------------------------------------
    # Pivot Tables
    # -------------------------------------------------------------------------

    def create_pivot_table(self, pivot_config: Dict[str, Any]) -> Dict[str, Any]:
        return self.pivot_engine.create_pivot_table(config=pivot_config)

    def get_pivot_tables(self) -> Dict[str, Any]:
        return self.pivot_engine.get_pivot_tables()

    def refresh_pivot_table(self, pivot_id: Optional[str] = None) -> Dict[str, Any]:
        return self.pivot_engine.refresh_pivot_table(table_name=pivot_id)

    def create_pivot_chart(self, pivot_config: Dict[str, Any]) -> Dict[str, Any]:
        return self.pivot_engine.create_pivot_chart(config=pivot_config)

    # -------------------------------------------------------------------------
    # Tables (ListObjects)
    # -------------------------------------------------------------------------

    def create_table(self, range_address: str, table_name: Optional[str] = None) -> Dict[str, Any]:
        return self.table_engine.create_table(range_address=range_address, table_name=table_name)

    def get_tables(self) -> Dict[str, Any]:
        return self.table_engine.get_tables()

    def format_table(self, table_name: str, style_name: str) -> Dict[str, Any]:
        return self.table_engine.set_table_style(table_name=table_name, style_name=style_name)

    # -------------------------------------------------------------------------
    # Data Validation
    # -------------------------------------------------------------------------

    def add_dropdown_validation(self, range_address: str, values: List[str]) -> Dict[str, Any]:
        return self.dv_engine.add_dropdown_validation(range_address=range_address, values=values)

    def add_data_validation(self, range_address: str, validation_config: Dict[str, Any]) -> Dict[str, Any]:
        return self.dv_engine.add_data_validation(range_address=range_address, config=validation_config)

    def inspect_data_validation(self, range_address: str) -> Dict[str, Any]:
        return self.dv_engine.inspect_data_validation(range_address=range_address)

    # -------------------------------------------------------------------------
    # Sorting & Filtering
    # -------------------------------------------------------------------------

    def sort_range(self, range_address: str, sort_config: Dict[str, Any]) -> Dict[str, Any]:
        return self.sort_filter_engine.sort_range(range_address=range_address, config=sort_config)

    def apply_filter(self, range_address: str, filter_config: Dict[str, Any]) -> Dict[str, Any]:
        return self.sort_filter_engine.apply_auto_filter(
            range_address=range_address,
            field_index=filter_config.get("field_index", 1),
            criteria1=filter_config.get("criteria", ""),
        )

    def clear_filters(self) -> Dict[str, Any]:
        return self.sort_filter_engine.clear_filters()

    # -------------------------------------------------------------------------
    # Data Cleaning
    # -------------------------------------------------------------------------

    def remove_duplicates(
        self,
        range_address: Optional[str] = None,
        columns: Optional[List[int]] = None,
        confirmed: bool = False,
    ) -> Dict[str, Any]:
        return self.data_cleaner.remove_duplicates(range_address=range_address, columns=columns, confirmed=confirmed)

    def generate_data_quality_report(self, range_address: Optional[str] = None) -> Dict[str, Any]:
        return self.data_cleaner.generate_data_quality_report(range_address=range_address)

    # -------------------------------------------------------------------------
    # Named Ranges
    # -------------------------------------------------------------------------

    def create_named_range(self, name: str, range_address: str) -> Dict[str, Any]:
        return self.named_range_engine.create_named_range(name=name, range_address=range_address)

    def get_named_ranges(self) -> Dict[str, Any]:
        return self.named_range_engine.get_named_ranges()

    def delete_named_range(self, name: str) -> Dict[str, Any]:
        return self.named_range_engine.delete_named_range(name=name)

    # -------------------------------------------------------------------------
    # Data Intelligence & Analysis (Section 22)
    # -------------------------------------------------------------------------

    def analyze_dataset(self, range_address: Optional[str] = None) -> Dict[str, Any]:
        """Bounded statistical and data profiling summary of range."""
        qr = self.data_cleaner.generate_data_quality_report(range_address)
        return {
            "status": "SUCCESS",
            "range": qr.get("range"),
            "total_rows": qr.get("total_rows"),
            "total_columns": qr.get("total_columns"),
            "completeness": qr.get("completeness_percentage"),
            "data_summary": qr,
        }

    def summarize_dataset(self, range_address: Optional[str] = None) -> Dict[str, Any]:
        """Return dataset headers and preview rows."""
        vals_res = self.range_engine.get_range_values(range_address or "A1:E20")
        vals = vals_res.get("values", [])
        headers = vals[0] if len(vals) > 0 else []
        preview = vals[1:6] if len(vals) > 1 else []
        return {
            "status": "SUCCESS",
            "range": vals_res.get("range"),
            "headers": headers,
            "sample_rows": preview,
        }

    def generate_data_insights(self, range_address: Optional[str] = None) -> Dict[str, Any]:
        """Suggest optimal charts, formulas, and pivots based on dataset geometry."""
        qr = self.data_cleaner.generate_data_quality_report(range_address)
        num_cells = qr.get("numeric_cells", 0)
        text_cells = qr.get("text_cells", 0)

        suggested_charts = []
        if num_cells > 0 and text_cells > 0:
            suggested_charts.append("CLUSTERED_COLUMN")
            suggested_charts.append("PIE")
        if num_cells > 10:
            suggested_charts.append("LINE")

        return {
            "status": "SUCCESS",
            "suggested_charts": suggested_charts,
            "suggested_pivot": bool(num_cells > 0 and text_cells > 0),
            "suggested_formulas": ["SUM", "AVERAGE", "COUNTIF"],
        }

    # -------------------------------------------------------------------------
    # Reports
    # -------------------------------------------------------------------------

    def generate_report(self, report_config: Dict[str, Any]) -> Dict[str, Any]:
        rtype = report_config.get("report_type", "MONTHLY_SALES").upper()
        if rtype == "KPI_DASHBOARD":
            return self.report_engine.generate_kpi_dashboard(
                title=report_config.get("title", "KPI Dashboard"),
                sheet_name=report_config.get("destination_sheet", "KPI_Dashboard"),
            )
        else:
            return self.report_engine.generate_sales_report(
                title=report_config.get("title", "Monthly Sales Executive Report"),
                period=report_config.get("period", "Q4 2026"),
                sheet_name=report_config.get("destination_sheet", "Sales_Report"),
            )

    def generate_kpi_dashboard(self, report_config: Dict[str, Any]) -> Dict[str, Any]:
        return self.report_engine.generate_kpi_dashboard(
            title=report_config.get("title", "Enterprise Operational Dashboard"),
            sheet_name=report_config.get("destination_sheet", "KPI_Dashboard"),
        )

    # -------------------------------------------------------------------------
    # PDF Export
    # -------------------------------------------------------------------------

    def export_pdf(self, output_path: str, export_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        scope = (export_config or {}).get("scope", "worksheet").lower()
        if scope == "workbook":
            return self.print_engine.export_workbook_to_pdf(output_path=output_path)
        return self.print_engine.export_worksheet_to_pdf(output_path=output_path)
