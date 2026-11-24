"""
Advanced Pivot Table & Pivot Chart Engine for Microsoft Excel — Zye Day 22.
Creates PivotCaches, dynamic PivotTables, field aggregations, and linked PivotCharts.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union
from zye_office.excel.excel_adapter import ExcelAdapter
from zye_office.excel.excel_constants import ExcelConstants
from zye_office.excel.excel_errors import (
    ExcelNoActiveWorksheetError,
    ExcelPivotError,
    ExcelSheetProtectedError,
)
from zye_office.excel.excel_validator import ExcelValidator
from zye_office.models.excel_models import ExcelPivotConfig

logger = logging.getLogger("zye.office.excel.pivot")

AGGREGATION_MAP = {
    "SUM": ExcelConstants.xlSum,
    "COUNT": ExcelConstants.xlCount,
    "AVERAGE": ExcelConstants.xlAverage,
    "MAX": ExcelConstants.xlMax,
    "MIN": ExcelConstants.xlMin,
    "PRODUCT": ExcelConstants.xlProduct,
    "STDEV": ExcelConstants.xlStDev,
    "VAR": ExcelConstants.xlVar,
}


class ExcelPivotEngine:
    """Manages Microsoft Excel PivotCaches, PivotTables, and PivotCharts."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        validator: Optional[ExcelValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or ExcelValidator()

    def create_pivot_table(
        self,
        config: Union[ExcelPivotConfig, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Create a native Pivot Table from a source tabular range."""
        if isinstance(config, dict):
            cfg = ExcelPivotConfig(**config)
        else:
            cfg = config

        valid_source = self.validator.validate_range_address(cfg.source_range)

        def _sta_create_pivot() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            wb = self.adapter.get_active_workbook_raw()
            if wb is None:
                raise ExcelPivotError("No active workbook available for Pivot Table creation.")

            src_ws = self.adapter.get_active_worksheet_raw()
            if src_ws is None:
                raise ExcelNoActiveWorksheetError()

            source_rng = src_ws.Range(valid_source)

            # Determine destination worksheet
            dest_ws = src_ws
            if cfg.destination_sheet:
                # Find or create destination sheet
                dest_sheet_name = cfg.destination_sheet.strip()
                dest_ws = None
                for s in wb.Worksheets:
                    if s.Name.lower() == dest_sheet_name.lower():
                        dest_ws = s
                        break
                if dest_ws is None:
                    dest_ws = wb.Worksheets.Add(After=wb.Worksheets(wb.Worksheets.Count))
                    dest_ws.Name = dest_sheet_name

            dest_cell = dest_ws.Range(cfg.destination_cell or "A3")

            # 1. Create Pivot Cache (SourceType = xlDatabase = 1)
            # PivotCaches().Create(SourceType=1, SourceData=source_rng)
            try:
                pc = wb.PivotCaches().Create(
                    SourceType=1,
                    SourceData=source_rng,
                    Version=5,  # xlPivotTableVersion15 / Excel 2013+
                )
            except Exception as exc:
                # Fallback to default version if 5 is rejected
                try:
                    pc = wb.PivotCaches().Create(SourceType=1, SourceData=source_rng)
                except Exception as exc2:
                    raise ExcelPivotError(f"Failed to create Pivot Cache: {exc2}")

            # 2. Create Pivot Table
            try:
                pt = pc.CreatePivotTable(
                    TableDestination=dest_cell,
                    TableName=cfg.table_name,
                )
            except Exception as exc:
                raise ExcelPivotError(f"Failed to instantiate Pivot Table: {exc}")

            # 3. Configure Row Fields
            for r_name in cfg.row_fields:
                try:
                    rf = pt.PivotFields(r_name)
                    rf.Orientation = ExcelConstants.xlRowField
                except Exception as exc:
                    logger.warning("Could not set row field '%s': %s", r_name, exc)

            # 4. Configure Column Fields
            for c_name in cfg.column_fields:
                try:
                    cf = pt.PivotFields(c_name)
                    cf.Orientation = ExcelConstants.xlColumnField
                except Exception as exc:
                    logger.warning("Could not set column field '%s': %s", c_name, exc)

            # 5. Configure Filter / Page Fields
            for f_name in cfg.filter_fields:
                try:
                    ff = pt.PivotFields(f_name)
                    ff.Orientation = ExcelConstants.xlPageField
                except Exception as exc:
                    logger.warning("Could not set filter field '%s': %s", f_name, exc)

            # 6. Configure Value Fields & Aggregations
            for vf_dict in cfg.value_fields:
                vf_name = vf_dict.get("field", "")
                agg_name = vf_dict.get("aggregation", "SUM").upper()
                agg_func = AGGREGATION_MAP.get(agg_name, ExcelConstants.xlSum)
                try:
                    data_field = pt.AddDataField(
                        pt.PivotFields(vf_name),
                        f"{agg_name} of {vf_name}",
                        agg_func,
                    )
                except Exception as exc:
                    logger.warning("Could not add value field '%s': %s", vf_name, exc)

            # Refresh
            pt.Update()

            return {
                "status": "SUCCESS",
                "table_name": pt.Name,
                "destination_sheet": dest_ws.Name,
                "destination_cell": cfg.destination_cell or "A3",
                "row_fields": cfg.row_fields,
                "column_fields": cfg.column_fields,
                "value_fields": cfg.value_fields,
            }

        return self.worker.run(_sta_create_pivot)

    def refresh_pivot_table(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Refresh a pivot table or all pivot tables in active worksheet."""
        def _sta_refresh() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            refreshed = []
            pts = ws.PivotTables()
            for i in range(1, pts.Count + 1):
                pt = pts(i)
                if table_name is None or pt.Name.lower() == table_name.lower():
                    pt.Update()
                    refreshed.append(pt.Name)

            return {
                "status": "SUCCESS",
                "refreshed_tables": refreshed,
            }

        return self.worker.run(_sta_refresh)

    def get_pivot_tables(self) -> Dict[str, Any]:
        """List all Pivot Tables in active worksheet."""
        def _sta_get_pts() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            pts = ws.PivotTables()
            tables = []
            for i in range(1, pts.Count + 1):
                pt = pts(i)
                tables.append({
                    "name": pt.Name,
                    "destination_range": pt.TableRange1.Address if hasattr(pt, "TableRange1") else None,
                })

            return {
                "status": "SUCCESS",
                "total_pivot_tables": len(tables),
                "pivot_tables": tables,
            }

        return self.worker.run(_sta_get_pts)

    def create_pivot_chart(
        self,
        config: Union[ExcelPivotConfig, Dict[str, Any]],
        chart_type: str = "CLUSTERED_COLUMN",
    ) -> Dict[str, Any]:
        """Create a Pivot Table and attach a linked native Pivot Chart."""
        pt_res = self.create_pivot_table(config)
        dest_sheet = pt_res.get("destination_sheet")

        def _sta_chart() -> Dict[str, Any]:
            wb = self.adapter.get_active_workbook_raw()
            ws = None
            for s in wb.Worksheets:
                if s.Name == dest_sheet:
                    ws = s
                    break
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            pt = ws.PivotTables(pt_res["table_name"])
            chart_obj = ws.ChartObjects().Add(400, 50, 450, 280)
            chart = chart_obj.Chart
            chart.SetSourceData(Source=pt.TableRange1)

            return {
                "status": "SUCCESS",
                "pivot_table": pt_res["table_name"],
                "pivot_chart_id": chart_obj.Index,
                "chart_name": chart_obj.Name,
            }

        return self.worker.run(_sta_chart)
