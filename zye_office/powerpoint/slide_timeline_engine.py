"""
Slide Timeline Engine for Microsoft PowerPoint — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointNoActivePresentationError,
)
from zye_office.powerpoint.powerpoint_validator import PowerPointValidator

logger = logging.getLogger("zye.office.powerpoint.timeline")


class PowerPointTimelineEngine:
    """Controls sequence ordering and clearing of animation effects."""

    def __init__(
        self,
        adapter: Optional[PowerPointAdapter] = None,
        validator: Optional[PowerPointValidator] = None,
    ) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or PowerPointValidator()

    def clear_timeline(self, slide_index: int) -> Dict[str, Any]:
        """Clear all animations from a slide."""
        def _sta_clear() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)
            seq = s.TimeLine.MainSequence
            initial_count = seq.Count
            while seq.Count > 0:
                seq(1).Delete()

            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "cleared_effects": initial_count,
            }

        return self.worker.run(_sta_clear)

    def set_animation_order(self, slide_index: int, from_index: int, to_index: int) -> Dict[str, Any]:
        """Move an animation effect to a new sequence order index."""
        def _sta_reorder() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)
            seq = s.TimeLine.MainSequence
            if from_index <= seq.Count:
                seq(from_index).MoveTo(to_index)

            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "from_index": from_index,
                "to_index": to_index,
            }

        return self.worker.run(_sta_reorder)
