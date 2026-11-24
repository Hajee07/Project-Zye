"""
Chart Engine for Microsoft PowerPoint — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointNoActivePresentationError,
)
from zye_office.powerpoint.powerpoint_validator import PowerPointValidator

logger = logging.getLogger("zye.office.powerpoint.charts")

PPT_CHART_MAP = {
    "column": 51,  # xlColumnClustered
    "bar": 57,     # xlBarClustered
    "line": 4,     # xlLine
    "pie": 5,      # xlPie
    "doughnut": -4120,
}


class PowerPointChartEngine:
    """Manages embedded presentation charts."""

    def __init__(
        self,
        adapter: Optional[PowerPointAdapter] = None,
        validator: Optional[PowerPointValidator] = None,
    ) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or PowerPointValidator()

    def add_chart(
        self,
        slide_index: int,
        chart_type: str = "column",
        title: Optional[str] = None,
        left: float = 120.0,
        top: float = 120.0,
        width: float = 720.0,
        height: float = 340.0,
    ) -> Dict[str, Any]:
        """Insert a native presentation chart onto a slide."""
        ct_enum = PPT_CHART_MAP.get(chart_type.lower(), 51)

        def _sta_chart() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)

            # AddChart2(Style, Type, Left, Top, Width, Height)
            sh = s.Shapes.AddChart2(-1, ct_enum, left, top, width, height)
            chart = sh.Chart

            if title:
                chart.HasTitle = True
                chart.ChartTitle.Text = title

            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "chart_name": sh.Name,
                "chart_type": chart_type,
            }

        return self.worker.run(_sta_chart)
