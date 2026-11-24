"""
PDF Export & Print Execution Engine for Microsoft Excel — Zye Day 22.
Exports active worksheets, workbooks, or print areas to high-fidelity PDF documents.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional
from zye_office.excel.excel_adapter import ExcelAdapter
from zye_office.excel.excel_constants import ExcelConstants
from zye_office.excel.excel_errors import (
    ExcelNoActiveWorkbookError,
    ExcelNoActiveWorksheetError,
    ExcelSecurityError,
)
from zye_office.excel.excel_validator import ExcelValidator
from zye_office.file_exporter import OfficeFileExporter
from zye_office.path_validator import OfficePathValidator

logger = logging.getLogger("zye.office.excel.print_engine")


class ExcelPrintEngine:
    """Manages high-fidelity PDF exports and print preparation."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        exporter: Optional[OfficeFileExporter] = None,
        path_validator: Optional[OfficePathValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.path_validator = path_validator or OfficePathValidator()
        self.exporter = exporter

    def export_worksheet_to_pdf(
        self,
        output_path: str,
        overwrite: bool = True,
    ) -> Dict[str, Any]:
        """Export active worksheet to PDF file."""
        norm_pdf = self.path_validator.validate_path(output_path, allowed_extensions=[".pdf"])

        def _sta_export_ws() -> Dict[str, Any]:
            ws = self.adapter.get_active_worksheet_raw()
            if ws is None:
                raise ExcelNoActiveWorksheetError()

            if os.path.exists(norm_pdf) and not overwrite:
                raise ExcelSecurityError(f"PDF destination '{norm_pdf}' already exists.")

            # xlTypePDF = 0
            ws.ExportAsFixedFormat(
                Type=ExcelConstants.xlTypePDF,
                Filename=norm_pdf,
                Quality=0,  # xlQualityStandard
                IncludeDocProperties=True,
                IgnorePrintAreas=False,
                OpenAfterPublish=False,
            )

            if not os.path.exists(norm_pdf) or os.path.getsize(norm_pdf) == 0:
                raise ExcelSecurityError("Export failed: PDF file was not created or is 0 bytes.")

            return {
                "status": "SUCCESS",
                "pdf_path": norm_pdf,
                "file_size_bytes": os.path.getsize(norm_pdf),
                "sheet_name": ws.Name,
            }

        return self.worker.run(_sta_export_ws)

    def export_workbook_to_pdf(
        self,
        output_path: str,
        overwrite: bool = True,
    ) -> Dict[str, Any]:
        """Export entire active workbook (all sheets) to PDF."""
        norm_pdf = self.path_validator.validate_path(output_path, allowed_extensions=[".pdf"])

        def _sta_export_wb() -> Dict[str, Any]:
            wb = self.adapter.get_active_workbook_raw()
            if wb is None:
                raise ExcelNoActiveWorkbookError()

            if os.path.exists(norm_pdf) and not overwrite:
                raise ExcelSecurityError(f"PDF destination '{norm_pdf}' already exists.")

            wb.ExportAsFixedFormat(
                Type=ExcelConstants.xlTypePDF,
                Filename=norm_pdf,
                Quality=0,
                IncludeDocProperties=True,
                IgnorePrintAreas=False,
                OpenAfterPublish=False,
            )

            if not os.path.exists(norm_pdf) or os.path.getsize(norm_pdf) == 0:
                raise ExcelSecurityError("Export failed: Workbook PDF was not created or is 0 bytes.")

            return {
                "status": "SUCCESS",
                "pdf_path": norm_pdf,
                "file_size_bytes": os.path.getsize(norm_pdf),
                "workbook_name": wb.Name,
            }

        return self.worker.run(_sta_export_wb)
