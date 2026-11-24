"""
Slide Formatting & Preset Engine for Microsoft PowerPoint — Zye Day 23.
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

logger = logging.getLogger("zye.office.powerpoint.formatting")


class PowerPointFormattingEngine:
    """Manages typography, background colors, and slide theme presets."""

    def __init__(
        self,
        adapter: Optional[PowerPointAdapter] = None,
        validator: Optional[PowerPointValidator] = None,
    ) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or PowerPointValidator()

    def format_text(
        self,
        slide_index: int,
        shape_identifier: Any = "Title",
        font_name: Optional[str] = None,
        font_size: Optional[float] = None,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        color_bgr: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Apply formatting to text range in a shape."""
        def _sta_fmt() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)

            shape = None
            if str(shape_identifier).lower() == "title" and s.Shapes.HasTitle:
                shape = s.Shapes.Title
            else:
                shape = s.Shapes(shape_identifier)

            font = shape.TextFrame.TextRange.Font
            if font_name:
                font.Name = font_name
            if font_size:
                font.Size = font_size
            if bold is not None:
                font.Bold = -1 if bold else 0
            if italic is not None:
                font.Italic = -1 if italic else 0
            if color_bgr is not None:
                font.Color.RGB = color_bgr

            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "shape": shape.Name,
            }

        return self.worker.run(_sta_fmt)

    def set_slide_background(self, slide_index: int, color_bgr: int) -> Dict[str, Any]:
        """Set solid background fill color for a slide."""
        def _sta_bg() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)
            s.FollowMasterBackground = 0  # msoFalse
            s.Background.Fill.Solid()
            s.Background.Fill.ForeColor.RGB = color_bgr

            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "background_color_bgr": color_bgr,
            }

        return self.worker.run(_sta_bg)
