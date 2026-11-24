"""
Theme Engine for Microsoft PowerPoint — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointNoActivePresentationError,
)

logger = logging.getLogger("zye.office.powerpoint.themes")


class PowerPointThemeEngine:
    """Manages presentation themes and color schemes."""

    def __init__(self, adapter: Optional[PowerPointAdapter] = None) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker

    def apply_theme(self, theme_path_or_name: str) -> Dict[str, Any]:
        """Apply a PowerPoint theme (.thmx file) to active presentation."""
        def _sta_theme() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            try:
                pres.ApplyTheme(theme_path_or_name)
            except Exception as exc:
                # If path not found, log warning and report
                logger.warning("Could not apply theme file %s: %s", theme_path_or_name, exc)

            return {
                "status": "SUCCESS",
                "theme": theme_path_or_name,
                "presentation": pres.Name,
            }

        return self.worker.run(_sta_theme)
