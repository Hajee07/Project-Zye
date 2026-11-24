"""
Slide Layout Engine for Microsoft PowerPoint — Zye Day 23.
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

logger = logging.getLogger("zye.office.powerpoint.layout")

LAYOUT_MAP = {
    "title": PowerPointConstants.ppLayoutTitle,
    "title_and_content": PowerPointConstants.ppLayoutText,
    "two_content": PowerPointConstants.ppLayoutTwoColumnText,
    "comparison": PowerPointConstants.ppLayoutComparison,
    "title_only": PowerPointConstants.ppLayoutTitleOnly,
    "blank": PowerPointConstants.ppLayoutBlank,
}


class PowerPointLayoutEngine:
    """Controls slide layout applications."""

    def __init__(
        self,
        adapter: Optional[PowerPointAdapter] = None,
        validator: Optional[PowerPointValidator] = None,
    ) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or PowerPointValidator()

    def change_layout(self, slide_index: int, layout_name: str) -> Dict[str, Any]:
        """Apply a standard layout to an existing slide."""
        norm_layout = layout_name.lower().strip()
        layout_enum = LAYOUT_MAP.get(norm_layout, PowerPointConstants.ppLayoutText)

        def _sta_layout() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)
            s.Layout = layout_enum
            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "layout": norm_layout,
            }

        return self.worker.run(_sta_layout)
