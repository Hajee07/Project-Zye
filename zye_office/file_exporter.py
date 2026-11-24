"""
Zye Office File Exporter
Native COM-driven PDF export foundation for Microsoft Word, Excel, and PowerPoint.
Enforces canonical path validation, overwrite confirmation, and post-export verification.
"""

from typing import Dict, Any, Optional
import os
import time

from zye_office.models import OfficeAppType, PDFExportResult
from zye_office.errors import (
    OfficeFileExportError,
    OfficeValidationError,
    OfficeCOMError,
    format_office_error,
)
from zye_office.com_runtime import OfficeCOMRuntime
from zye_office.session_manager import OfficeSessionManager
from zye_office.path_validator import OfficePathValidator


class OfficeFileExporter:
    """
    Exports active Office documents to PDF using native COM ExportAsFixedFormat/SaveAs APIs.
    """

    # Office COM Format Constants
    WD_EXPORT_FORMAT_PDF = 17
    XL_TYPE_PDF = 0
    PP_SAVE_AS_PDF = 32
    PP_FIXED_FORMAT_TYPE_PDF = 2

    def __init__(
        self,
        runtime: OfficeCOMRuntime,
        session_manager: OfficeSessionManager,
        path_validator: Optional[OfficePathValidator] = None,
    ):
        self.runtime = runtime
        self.session_manager = session_manager
        self.path_validator = path_validator or OfficePathValidator()

    def export_active_to_pdf(
        self,
        session_id: str,
        output_path: str,
        overwrite: bool = False,
    ) -> PDFExportResult:
        """
        Exports the active document in the given session to PDF.
        Runs COM interaction inside the STA worker thread.
        """
        start_time = time.time()

        # 1. Session check
        session = self.session_manager.get_session(session_id)
        if not session or not session.is_active:
            raise OfficeValidationError(f"Invalid or inactive session ID: {session_id}")

        if session.app_type not in (OfficeAppType.WORD, OfficeAppType.EXCEL, OfficeAppType.POWERPOINT):
            raise OfficeValidationError(f"PDF export not supported for {session.app_type.value}")

        # 2. Path validation
        canonical_output = self.path_validator.validate_path(
            output_path,
            allowed_extensions=[".pdf"],
        )

        # 3. Overwrite check
        if os.path.exists(canonical_output) and not overwrite:
            raise OfficeFileExportError(
                f"Destination PDF '{canonical_output}' already exists. Pass overwrite=True to confirm overwrite."
            )

        # 4. Dispatch to STA worker
        try:
            pages = self.runtime.worker.run(
                self._export_internal,
                session_id=session_id,
                app_type=session.app_type,
                output_path=canonical_output,
            )

            # 5. Post-export verification
            if not os.path.exists(canonical_output):
                raise OfficeFileExportError(f"Export completed but output file not found at: {canonical_output}")

            file_size = os.path.getsize(canonical_output)
            if file_size <= 0:
                raise OfficeFileExportError(f"Exported PDF is zero bytes: {canonical_output}")

            elapsed_ms = (time.time() - start_time) * 1000

            self.session_manager.touch_session(session_id)

            return PDFExportResult(
                success=True,
                source_app=session.app_type,
                output_path=canonical_output,
                file_size_bytes=file_size,
                pages_exported=pages,
                elapsed_ms=round(elapsed_ms, 2),
            )
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            if isinstance(e, (OfficeFileExportError, OfficeValidationError)):
                raise
            raise OfficeFileExportError(f"PDF export failed on COM level: {e}") from e

    def _export_internal(self, session_id: str, app_type: OfficeAppType, output_path: str) -> Optional[int]:
        """Runs within the STA worker thread."""
        app = self.runtime.get_app_instance(session_id)
        if not app:
            raise OfficeCOMError(f"COM instance for session '{session_id}' not found in worker cache")

        # Ensure parent directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        if app_type == OfficeAppType.WORD:
            if app.Documents.Count == 0:
                raise OfficeCOMError("No open Word document to export")
            doc = app.ActiveDocument
            try:
                # Primary method: ExportAsFixedFormat
                # ExportFormat=17 (wdExportFormatPDF), OpenAfterExport=False
                doc.ExportAsFixedFormat(
                    OutputFileName=output_path,
                    ExportFormat=self.WD_EXPORT_FORMAT_PDF,
                    OpenAfterExport=False,
                    OptimizeFor=0,  # wdExportOptimizeForPrint
                )
            except Exception:
                # Fallback method: SaveAs
                doc.SaveAs(output_path, FileFormat=self.WD_EXPORT_FORMAT_PDF)

            try:
                # Attempt to read page count for reporting
                wdStatisticPages = 2
                return int(doc.ComputeStatistics(wdStatisticPages))
            except Exception:
                return None

        elif app_type == OfficeAppType.EXCEL:
            if app.Workbooks.Count == 0:
                raise OfficeCOMError("No open Excel workbook to export")
            wb = app.ActiveWorkbook
            # Type=0 (xlTypePDF), Filename=output_path, OpenAfterPublish=False
            wb.ExportAsFixedFormat(
                Type=self.XL_TYPE_PDF,
                Filename=output_path,
                OpenAfterPublish=False,
            )
            try:
                return int(wb.Sheets.Count)
            except Exception:
                return None

        elif app_type == OfficeAppType.POWERPOINT:
            if app.Presentations.Count == 0:
                raise OfficeCOMError("No open PowerPoint presentation to export")
            pres = app.ActivePresentation
            try:
                # ppFixedFormatTypePDF = 2
                pres.ExportAsFixedFormat(
                    Path=output_path,
                    FixedFormatType=self.PP_FIXED_FORMAT_TYPE_PDF,
                    PrintRange=None,
                )
            except Exception:
                # Fallback: SaveAs with 32 (ppSaveAsPDF)
                pres.SaveAs(output_path, self.PP_SAVE_AS_PDF)

            try:
                return int(pres.Slides.Count)
            except Exception:
                return None

        return None
