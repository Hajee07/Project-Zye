"""
Slide Management Engine for Microsoft PowerPoint — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.powerpoint_constants import PowerPointConstants
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointNoActivePresentationError,
    PowerPointSlideNotFoundError,
)
from zye_office.powerpoint.powerpoint_validator import PowerPointValidator

logger = logging.getLogger("zye.office.powerpoint.slides")


class PowerPointSlideManager:
    """Manages slide addition, duplication, deletion, moving, and enumeration."""

    def __init__(
        self,
        adapter: Optional[PowerPointAdapter] = None,
        validator: Optional[PowerPointValidator] = None,
    ) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or PowerPointValidator()

    def get_all_slides(self) -> List[Dict[str, Any]]:
        """List all slides with metadata."""
        def _sta_get_slides() -> List[Dict[str, Any]]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            slides_list = []
            for i in range(1, pres.Slides.Count + 1):
                s = pres.Slides(i)
                title = s.Shapes.Title.TextFrame.TextRange.Text.strip() if s.Shapes.HasTitle else f"Slide {i}"
                slides_list.append({
                    "slide_index": i,
                    "slide_id": getattr(s, "SlideID", i),
                    "title": title,
                    "shape_count": s.Shapes.Count,
                    "is_hidden": getattr(s.SlideShowTransition, "Hidden", False) == -1,
                })
            return slides_list

        return self.worker.run(_sta_get_slides)

    def add_slide(self, layout: int = PowerPointConstants.ppLayoutText) -> Dict[str, Any]:
        """Add a new slide at the end of the presentation."""
        def _sta_add() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            new_idx = pres.Slides.Count + 1
            s = pres.Slides.Add(Index=new_idx, Layout=layout)
            return {
                "status": "SUCCESS",
                "slide_index": s.SlideIndex,
                "total_slides": pres.Slides.Count,
            }

        return self.worker.run(_sta_add)

    def duplicate_slide(self, slide_index: int) -> Dict[str, Any]:
        """Duplicate an existing slide."""
        def _sta_dup() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            target_s = pres.Slides(slide_index)
            target_s.Duplicate()
            return {
                "status": "SUCCESS",
                "duplicated_slide_index": slide_index,
                "new_slide_index": slide_index + 1,
                "total_slides": pres.Slides.Count,
            }

        return self.worker.run(_sta_dup)

    def delete_slide(self, slide_index: int, confirmed: bool = False) -> Dict[str, Any]:
        """Delete a slide with mandatory confirmation."""
        if not confirmed:
            raise ValueError(f"Deleting slide {slide_index} requires explicit confirmed=True.")

        def _sta_del() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            pres.Slides(slide_index).Delete()
            return {
                "status": "SUCCESS",
                "deleted_slide_index": slide_index,
                "remaining_slides": pres.Slides.Count,
            }

        return self.worker.run(_sta_del)

    def move_slide(self, from_index: int, to_index: int) -> Dict[str, Any]:
        """Move a slide to a new position index."""
        def _sta_move() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(from_index, pres.Slides.Count)
            pres.Slides(from_index).MoveTo(to_index)
            return {
                "status": "SUCCESS",
                "original_index": from_index,
                "new_index": to_index,
            }

        return self.worker.run(_sta_move)

    def hide_slide(self, slide_index: int, hide: bool = True) -> Dict[str, Any]:
        """Hide or unhide a slide during slide show."""
        def _sta_hide() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)
            s.SlideShowTransition.Hidden = -1 if hide else 0
            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "is_hidden": hide,
            }

        return self.worker.run(_sta_hide)

    def get_slide_text(self, slide_index: int) -> Dict[str, Any]:
        """Extract all textual contents from shapes on the slide."""
        def _sta_text() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)
            texts = []
            title = None
            for shape in s.Shapes:
                try:
                    if shape.HasTextFrame and shape.TextFrame.HasText:
                        txt = shape.TextFrame.TextRange.Text.strip()
                        if txt:
                            texts.append(txt)
                            if s.Shapes.HasTitle and shape == s.Shapes.Title:
                                title = txt
                except Exception:
                    pass

            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "title": title,
                "text_content": texts,
            }

        return self.worker.run(_sta_text)
