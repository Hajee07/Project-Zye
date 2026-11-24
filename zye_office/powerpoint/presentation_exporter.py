"""
High-Fidelity PDF & Media Exporter for Microsoft PowerPoint — Zye Day 23.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional
from zye_office.path_validator import OfficePathValidator
from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.powerpoint_constants import PowerPointConstants
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointNoActivePresentationError,
)

logger = logging.getLogger("zye.office.powerpoint.exporter")


class PowerPointExporter:
    """Exports presentations to standalone PDF documents with size verification."""

    def __init__(
        self,
        adapter: Optional[PowerPointAdapter] = None,
        path_validator: Optional[OfficePathValidator] = None,
    ) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker
        self.path_validator = path_validator or OfficePathValidator()

    def export_pdf(self, output_path: str, overwrite: bool = True) -> Dict[str, Any]:
        """Export active presentation to PDF format."""
        norm_pdf = self.path_validator.validate_path(output_path, allowed_extensions=[".pdf"])
        if os.path.exists(norm_pdf) and not overwrite:
            raise FileExistsError(f"PDF destination '{norm_pdf}' already exists.")

        def _sta_export() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            # ppSaveAsPDF = 32
            pres.SaveAs(FileName=norm_pdf, FileFormat=PowerPointConstants.ppSaveAsPDF)

            if not os.path.exists(norm_pdf) or os.path.getsize(norm_pdf) == 0:
                raise IOError(f"Failed to create valid non-empty PDF at: {norm_pdf}")

            return {
                "status": "SUCCESS",
                "pdf_path": norm_pdf,
                "file_size_bytes": os.path.getsize(norm_pdf),
                "presentation_name": pres.Name,
                "slide_count": pres.Slides.Count,
            }

        return self.worker.run(_sta_export)
