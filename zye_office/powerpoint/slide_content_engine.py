"""
Slide Content & Typography Engine for Microsoft PowerPoint — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointNoActivePresentationError,
)
from zye_office.powerpoint.powerpoint_validator import PowerPointValidator

logger = logging.getLogger("zye.office.powerpoint.content")


class PowerPointContentEngine:
    """Manages slide titles, body text, and bulleted lists."""

    def __init__(
        self,
        adapter: Optional[PowerPointAdapter] = None,
        validator: Optional[PowerPointValidator] = None,
    ) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or PowerPointValidator()

    def set_slide_title(self, slide_index: int, title: str) -> Dict[str, Any]:
        """Set or update the slide title."""
        def _sta_title() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)
            if not s.Shapes.HasTitle:
                s.Shapes.AddTitle()
            s.Shapes.Title.TextFrame.TextRange.Text = title
            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "title": title,
            }

        return self.worker.run(_sta_title)

    def add_slide_text(self, slide_index: int, text: str) -> Dict[str, Any]:
        """Add paragraph text to the content placeholder or textbox."""
        def _sta_add_text() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)

            # Try to find body placeholder (Placeholders(2))
            try:
                body_shape = s.Placeholders(2)
                body_shape.TextFrame.TextRange.Text = text
            except Exception:
                # Add a textbox if no placeholder exists
                tb = s.Shapes.AddTextbox(1, 100, 150, 760, 300)
                tb.TextFrame.TextRange.Text = text

            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "text": text,
            }

        return self.worker.run(_sta_add_text)

    def add_bullet_points(self, slide_index: int, bullets: List[str]) -> Dict[str, Any]:
        """Append a list of bullet points to the slide content."""
        def _sta_bullets() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)

            bullet_text = "\n".join(f"• {b}" for b in bullets)
            try:
                body_shape = s.Placeholders(2)
                body_shape.TextFrame.TextRange.Text = bullet_text
            except Exception:
                tb = s.Shapes.AddTextbox(1, 100, 150, 760, 300)
                tb.TextFrame.TextRange.Text = bullet_text

            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "bullet_count": len(bullets),
            }

        return self.worker.run(_sta_bullets)
