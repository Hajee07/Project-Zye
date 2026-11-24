"""
Shape Management Engine for Microsoft PowerPoint — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.powerpoint_constants import PowerPointConstants
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointNoActivePresentationError,
)
from zye_office.powerpoint.powerpoint_validator import PowerPointValidator

logger = logging.getLogger("zye.office.powerpoint.shapes")


class PowerPointShapeEngine:
    """Manages geometric shapes, textboxes, and object positioning."""

    def __init__(
        self,
        adapter: Optional[PowerPointAdapter] = None,
        validator: Optional[PowerPointValidator] = None,
    ) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or PowerPointValidator()

    def add_textbox(
        self,
        slide_index: int,
        text: str,
        left: float = 100.0,
        top: float = 100.0,
        width: float = 400.0,
        height: float = 100.0,
    ) -> Dict[str, Any]:
        """Add a custom floating textbox to a slide."""
        def _sta_tb() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)
            # AddTextbox(Orientation=1, Left, Top, Width, Height)
            tb = s.Shapes.AddTextbox(1, left, top, width, height)
            tb.TextFrame.TextRange.Text = text
            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "shape_name": tb.Name,
                "shape_id": tb.Id,
            }

        return self.worker.run(_sta_tb)

    def add_shape(
        self,
        slide_index: int,
        shape_type: str = "rectangle",
        left: float = 150.0,
        top: float = 150.0,
        width: float = 200.0,
        height: float = 120.0,
    ) -> Dict[str, Any]:
        """Add an AutoShape (rectangle, oval, rounded_rectangle) to a slide."""
        # 1 = Rectangle, 9 = Oval, 5 = RoundedRectangle
        st_enum = 1
        st_lower = shape_type.lower()
        if "oval" in st_lower or "circle" in st_lower:
            st_enum = 9
        elif "round" in st_lower:
            st_enum = 5

        def _sta_shape() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)
            sh = s.Shapes.AddShape(st_enum, left, top, width, height)
            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "shape_name": sh.Name,
                "shape_id": sh.Id,
            }

        return self.worker.run(_sta_shape)

    def delete_shape(self, slide_index: int, shape_identifier: Any) -> Dict[str, Any]:
        """Delete a shape by index or name."""
        def _sta_del() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)
            target = s.Shapes(shape_identifier)
            name = target.Name
            target.Delete()
            return {
                "status": "SUCCESS",
                "deleted_shape": name,
            }

        return self.worker.run(_sta_del)
