"""
Slide Master Engine for Microsoft PowerPoint — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointNoActivePresentationError,
)

logger = logging.getLogger("zye.office.powerpoint.master")


class PowerPointSlideMasterEngine:
    """Manages Slide Masters and global layout branding."""

    def __init__(self, adapter: Optional[PowerPointAdapter] = None) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker

    def inspect_slide_master(self) -> Dict[str, Any]:
        """Inspect active presentation slide master."""
        def _sta_inspect() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            master = pres.SlideMaster
            return {
                "status": "SUCCESS",
                "master_name": master.Name,
                "shape_count": master.Shapes.Count,
                "has_title": master.Shapes.HasTitle,
            }

        return self.worker.run(_sta_inspect)

    def set_master_footer(self, footer_text: str) -> Dict[str, Any]:
        """Update the global footer on the slide master."""
        def _sta_footer() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            for s in pres.Slides:
                try:
                    s.HeadersFooters.Footer.Text = footer_text
                    s.HeadersFooters.Footer.Visible = -1
                except Exception:
                    pass

            return {
                "status": "SUCCESS",
                "footer_text": footer_text,
            }

        return self.worker.run(_sta_footer)
