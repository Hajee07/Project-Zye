"""
Native Chart Engine for Microsoft Excel — Zye Day 22.
Creates, customizes, formats, and positions native 2D and 3D Excel charts via COM ChartObjects.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union
from zye_office.excel.excel_adapter import ExcelAdapter
from zye_office.excel.excel_constants import ExcelConstants
from zye_office.excel.excel_errors import (
    ExcelChartError,
    ExcelNoActiveWorksheetError,
    ExcelSheetProtectedError,
)
from zye_office.excel.excel_validator import ExcelValidator
from zye_office.models.excel_models import ExcelChartConfig

logger = logging.getLogger("zye.office.excel.chart")

CHART_TYPE_MAP = {
    "CLUSTERED_COLUMN": ExcelConstants.xlColumnClustered,
    "STACKED_COLUMN": ExcelConstants.xlColumnStacked,
    "PERCENT_STACKED_COLUMN": ExcelConstants.xlColumnStacked100,
    "CLUSTERED_BAR": ExcelConstants.xlBarClustered,
    "STACKED_BAR": ExcelConstants.xlBarStacked,
    "LINE": ExcelConstants.xlLine,
    "LINE_MARKERS": ExcelConstants.xlLineMarkers,
    "PIE": ExcelConstants.xlPie,
    "DOUGHNUT": ExcelConstants.xlDoughnut,
    "AREA": ExcelConstants.xlArea,
    "SCATTER": ExcelConstants.xlXYScatter,
    "THREE_D_COLUMN": ExcelConstants.xl3DColumnClustered,
    "THREE_D_BAR": ExcelConstants.xl3DBarClustered,
    "THREE_D_LINE": ExcelConstants.xl3DLine,
    "THREE_D_PIE": ExcelConstants.xl3DPie,
}

LEGEND_POS_MAP = {
    "bottom": ExcelConstants.xlLegendPositionBottom,
    "top": ExcelConstants.xlLegendPositionTop,
    "left": ExcelConstants.xlLegendPositionLeft,
    "right": ExcelConstants.xlLegendPositionRight,
}


class ExcelChartEngine:
    """Manages Excel ChartObjects, series mapping, axis titles, and visual presets."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        validator: Optional[ExcelValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or ExcelValidator()

    def create_chart(
        self,
        config: Union[ExcelChartConfig, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Create a native embedded Excel chart from source range."""
        if isinstance(config, dict):
            cfg = ExcelChartConfig(**config)
        else:
            cfg = config

        valid_source = self.validator.validate_range_address(cfg.source_range)
        chart_type_enum = CHART_TYPE_MAP.get(cfg.chart_type.upper(), ExcelConstants.xlColumnClustered)

        def _sta_create_chart() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            source_rng = ws.Range(valid_source)
            if source_rng.Cells.Count <= 1:
                raise ExcelChartError("Source range must contain multiple cells with headers and data.")

            # Default chart position next to or below source range if not specified
            left = cfg.left_points or (source_rng.Left + source_rng.Width + 20)
            top = cfg.top_points or source_rng.Top
            width = cfg.width_points or 380.0
            height = cfg.height_points or 240.0

            # ChartObjects.Add(Left, Top, Width, Height)
            chart_obj = ws.ChartObjects().Add(left, top, width, height)
            chart = chart_obj.Chart

            # Assign data source and chart type
            chart.SetSourceData(Source=source_rng)
            try:
                chart.ChartType = chart_type_enum
            except Exception as exc:
                logger.warning("Could not set chart type %s: %s", cfg.chart_type, exc)

            # Chart Title
            if cfg.title:
                chart.HasTitle = True
                chart.ChartTitle.Text = cfg.title

            # Axis Titles
            if cfg.x_title and hasattr(chart, "Axes"):
                try:
                    axis_x = chart.Axes(1)  # xlCategory = 1
                    axis_x.HasTitle = True
                    axis_x.AxisTitle.Text = cfg.x_title
                except Exception:
                    pass

            if cfg.y_title and hasattr(chart, "Axes"):
                try:
                    axis_y = chart.Axes(2)  # xlValue = 2
                    axis_y.HasTitle = True
                    axis_y.AxisTitle.Text = cfg.y_title
                except Exception:
                    pass

            # Legend
            if cfg.legend_position:
                if cfg.legend_position.lower() == "none":
                    chart.HasLegend = False
                else:
                    chart.HasLegend = True
                    pos = LEGEND_POS_MAP.get(cfg.legend_position.lower())
                    if pos:
                        try:
                            chart.Legend.Position = pos
                        except Exception:
                            pass

            # Data labels
            if cfg.data_labels:
                try:
                    chart.ApplyDataLabels()
                except Exception:
                    pass

            # Style ID
            if cfg.style_id:
                try:
                    chart.ChartStyle = cfg.style_id
                except Exception:
                    pass

            return {
                "status": "SUCCESS",
                "chart_id": chart_obj.Index,
                "chart_name": chart_obj.Name,
                "chart_type": cfg.chart_type,
                "source_range": valid_source,
                "title": cfg.title,
                "dimensions": {"width": width, "height": height, "left": left, "top": top},
            }

        return self.worker.run(_sta_create_chart)

    def get_charts(self) -> Dict[str, Any]:
        """List all charts in active worksheet."""
        def _sta_get_charts() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            chart_objs = ws.ChartObjects()
            charts_list = []
            for i in range(1, chart_objs.Count + 1):
                co = chart_objs(i)
                c = co.Chart
                title = c.ChartTitle.Text if c.HasTitle else None
                charts_list.append({
                    "chart_id": co.Index,
                    "chart_name": co.Name,
                    "title": title,
                    "has_legend": c.HasLegend,
                })

            return {
                "status": "SUCCESS",
                "total_charts": len(charts_list),
                "charts": charts_list,
            }

        return self.worker.run(_sta_get_charts)

    def delete_chart(self, chart_id: Union[int, str]) -> Dict[str, Any]:
        """Delete a chart by its index or name."""
        def _sta_del() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()
            if getattr(ws, "ProtectContents", False):
                raise ExcelSheetProtectedError()

            co = ws.ChartObjects(chart_id)
            name = co.Name
            co.Delete()
            return {
                "status": "SUCCESS",
                "deleted_chart": name,
            }

        return self.worker.run(_sta_del)
