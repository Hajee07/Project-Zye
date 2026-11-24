"""
Table Engine for Microsoft PowerPoint — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointNoActivePresentationError,
)
from zye_office.powerpoint.powerpoint_validator import PowerPointValidator

logger = logging.getLogger("zye.office.powerpoint.tables")


class PowerPointTableEngine:
    """Manages slide tables and cell data grids."""

    def __init__(
        self,
        adapter: Optional[PowerPointAdapter] = None,
        validator: Optional[PowerPointValidator] = None,
    ) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or PowerPointValidator()

    def add_table(
        self,
        slide_index: int,
        rows: int = 3,
        columns: int = 3,
        left: float = 100.0,
        top: float = 150.0,
        width: float = 760.0,
        height: float = 240.0,
        data: Optional[List[List[Any]]] = None,
    ) -> Dict[str, Any]:
        """Create a native PowerPoint table and populate with data."""
        def _sta_table() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)

            # AddTable(Rows, Columns, Left, Top, Width, Height)
            sh = s.Shapes.AddTable(rows, columns, left, top, width, height)
            tbl = sh.Table

            # Populate cells if data is provided
            if data:
                for r_idx, row in enumerate(data):
                    if r_idx >= rows:
                        break
                    for c_idx, val in enumerate(row):
                        if c_idx >= columns:
                            break
                        tbl.Cell(r_idx + 1, c_idx + 1).Shape.TextFrame.TextRange.Text = str(val or "")

            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "table_name": sh.Name,
                "rows": rows,
                "columns": columns,
            }

        return self.worker.run(_sta_table)
