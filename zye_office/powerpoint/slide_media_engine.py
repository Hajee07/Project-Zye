"""
Media Insertion Engine for Microsoft PowerPoint — Zye Day 23.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional
from zye_office.path_validator import OfficePathValidator
from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointNoActivePresentationError,
)
from zye_office.powerpoint.powerpoint_validator import PowerPointValidator

logger = logging.getLogger("zye.office.powerpoint.media")


class PowerPointMediaEngine:
    """Manages picture, audio, and video embedding in slides."""

    def __init__(
        self,
        adapter: Optional[PowerPointAdapter] = None,
        validator: Optional[PowerPointValidator] = None,
        path_validator: Optional[OfficePathValidator] = None,
    ) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or PowerPointValidator()
        self.path_validator = path_validator or OfficePathValidator()

    def insert_picture(
        self,
        slide_index: int,
        file_path: str,
        left: float = 150.0,
        top: float = 150.0,
        width: Optional[float] = 400.0,
        height: Optional[float] = 300.0,
    ) -> Dict[str, Any]:
        """Embed an image file onto a slide."""
        norm_path = self.path_validator.validate_path(file_path, allowed_extensions=[".png", ".jpg", ".jpeg", ".bmp", ".gif"])
        if not os.path.exists(norm_path):
            raise FileNotFoundError(f"Image not found at: {norm_path}")

        def _sta_pic() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)

            # AddPicture(FileName, LinkToFile, SaveWithDocument, Left, Top, Width, Height)
            w = width or -1
            h = height or -1
            pic = s.Shapes.AddPicture(norm_path, 0, -1, left, top, w, h)

            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "shape_name": pic.Name,
                "file_path": norm_path,
            }

        return self.worker.run(_sta_pic)
