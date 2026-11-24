"""
Speaker Notes Engine for Microsoft PowerPoint — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointNoActivePresentationError,
)
from zye_office.powerpoint.powerpoint_validator import PowerPointValidator

logger = logging.getLogger("zye.office.powerpoint.notes")


class PowerPointNotesEngine:
    """Manages presenter speaker notes on slides."""

    def __init__(
        self,
        adapter: Optional[PowerPointAdapter] = None,
        validator: Optional[PowerPointValidator] = None,
    ) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or PowerPointValidator()

    def add_notes(self, slide_index: int, notes_text: str) -> Dict[str, Any]:
        """Add or append speaker notes to a slide."""
        def _sta_notes() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)

            # NotesPage.Shapes.Placeholders(2) is the speaker notes body
            np = s.NotesPage
            np.Shapes.Placeholders(2).TextFrame.TextRange.Text = notes_text

            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "notes_text": notes_text,
            }

        return self.worker.run(_sta_notes)

    def get_notes(self, slide_index: int) -> Dict[str, Any]:
        """Read presenter speaker notes from a slide."""
        def _sta_get_notes() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)
            txt = ""
            try:
                txt = s.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text.strip()
            except Exception:
                pass

            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "notes_text": txt,
                "has_notes": bool(txt),
            }

        return self.worker.run(_sta_get_notes)
