"""
Universal Microsoft Excel COM Adapter — Zye Day 22.
Provides dedicated STA thread-bound access to Excel.Application COM interface.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.com_runtime import OfficeCOMRuntime
from zye_office.com_worker import STACOMWorker
from zye_office.excel.excel_errors import (
    ExcelCOMUnavailableError,
    ExcelNoActiveWorkbookError,
    ExcelNoActiveWorksheetError,
    ExcelNotInstalledError,
)
from zye_office.excel.excel_metadata import ExcelMetadataExtractor
from zye_office.excel.excel_validator import ExcelValidator
from zye_office.models import ConnectionPolicy

logger = logging.getLogger("zye.office.excel.adapter")


class ExcelAdapter:
    """Thread-safe COM Adapter for Microsoft Excel executing on dedicated STA worker."""

    def __init__(
        self,
        com_runtime: Optional[OfficeCOMRuntime] = None,
        worker: Optional[STACOMWorker] = None,
        validator: Optional[ExcelValidator] = None,
    ) -> None:
        self.worker = worker or STACOMWorker.get_instance()
        self.com_runtime = com_runtime or OfficeCOMRuntime(worker=self.worker)
        self.validator = validator or ExcelValidator()

    def connect(
        self,
        policy: ConnectionPolicy = ConnectionPolicy.AUTO_ATTACH_OR_LAUNCH,
    ) -> Dict[str, Any]:
        """Establish or attach to live Microsoft Excel COM application."""
        return self.com_runtime.connect_office_application("excel", policy=policy)

    def attach_existing_excel(self) -> Dict[str, Any]:
        """Attach only to an already running Excel process."""
        return self.connect(policy=ConnectionPolicy.ATTACH_EXISTING)

    def launch_excel(self) -> Dict[str, Any]:
        """Launch a fresh Excel instance."""
        return self.connect(policy=ConnectionPolicy.LAUNCH_NEW)

    def is_running(self) -> bool:
        """Check if Excel COM application is reachable or running."""
        try:
            return self.get_raw_app() is not None
        except Exception:
            return False

    def disconnect(self, quit_if_created_by_zye: bool = False) -> Dict[str, Any]:
        """Release COM references and optionally quit if launched by Zye."""
        return self.com_runtime.disconnect_office_application(
            "excel",
            quit_if_created_by_zye=quit_if_created_by_zye,
        )

    def get_raw_app(self) -> Any:
        """INTERNAL: Access raw Excel.Application COM dispatch inside STA worker."""
        return self.com_runtime.get_raw_com_object("excel")

    def get_active_workbook_raw(self) -> Any:
        """INTERNAL: Retrieve active Workbook dispatch inside STA worker."""
        app = self.get_raw_app()
        if app is None:
            conn = self.connect(policy=ConnectionPolicy.ATTACH_EXISTING)
            if conn.get("status") != "SUCCESS":
                return None
            app = self.get_raw_app()

        if app is None:
            return None

        try:
            if getattr(app.Workbooks, "Count", 0) > 0:
                return app.ActiveWorkbook
        except Exception as exc:
            logger.warning("Error accessing ActiveWorkbook in Excel: %s", exc)
        return None

    def get_active_worksheet_raw(self) -> Any:
        """INTERNAL: Retrieve active Worksheet dispatch inside STA worker."""
        app = self.get_raw_app()
        if app is None:
            wb = self.get_active_workbook_raw()
            if wb is None:
                return None
            app = self.get_raw_app()
        try:
            return getattr(app, "ActiveSheet", None)
        except Exception as exc:
            logger.warning("Error accessing ActiveSheet in Excel: %s", exc)
            return None

    # Public Safe Inspection Methods

    def inspect_excel_application(self) -> Dict[str, Any]:
        """Return structured state information about Excel instance."""
        def _sta_inspect() -> Dict[str, Any]:
            app = self.get_raw_app()
            if app is None:
                conn = self.connect(policy=ConnectionPolicy.ATTACH_EXISTING)
                if conn.get("status") != "SUCCESS":
                    return conn
                app = self.get_raw_app()

            if app is None:
                raise ExcelCOMUnavailableError()

            wb = None
            try:
                if app.Workbooks.Count > 0:
                    wb = app.ActiveWorkbook
            except Exception:
                pass

            meta = ExcelMetadataExtractor.extract_workbook_metadata(app, wb)
            return meta.model_dump()

        return self.worker.run(_sta_inspect)

    def get_open_workbooks(self) -> List[str]:
        """List filenames of all currently open workbooks."""
        def _sta_get_wbs() -> List[str]:
            app = self.get_raw_app()
            if app is None:
                return []
            names = []
            try:
                for wb in app.Workbooks:
                    names.append(wb.Name)
            except Exception:
                pass
            return names

        return self.worker.run(_sta_get_wbs)

    def get_open_worksheets(self) -> List[str]:
        """List worksheet names in active workbook."""
        def _sta_get_sheets() -> List[str]:
            wb = self.get_active_workbook_raw()
            if wb is None:
                return []
            names = []
            try:
                for ws in wb.Worksheets:
                    names.append(ws.Name)
            except Exception:
                pass
            return names

        return self.worker.run(_sta_get_sheets)

    def get_active_cell(self) -> Dict[str, Any]:
        """Get coordinates and value of currently focused cell."""
        def _sta_get_cell() -> Dict[str, Any]:
            app = self.get_raw_app()
            if app is None:
                raise ExcelCOMUnavailableError()
            try:
                cell = app.ActiveCell
                if cell is None:
                    return {"address": None, "value": None}
                return {
                    "address": getattr(cell, "Address", None),
                    "row": getattr(cell, "Row", 1),
                    "column": getattr(cell, "Column", 1),
                    "value": getattr(cell, "Value", None),
                    "formula": getattr(cell, "Formula", None),
                }
            except Exception as exc:
                return {"error": str(exc)}

        return self.worker.run(_sta_get_cell)

    def get_selected_range(self) -> Dict[str, Any]:
        """Get address and dimensions of current selection."""
        def _sta_get_sel() -> Dict[str, Any]:
            app = self.get_raw_app()
            if app is None:
                raise ExcelCOMUnavailableError()
            try:
                sel = app.Selection
                if sel is None:
                    return {"address": None}
                return {
                    "address": getattr(sel, "Address", None),
                    "row_count": getattr(sel.Rows, "Count", 1),
                    "column_count": getattr(sel.Columns, "Count", 1),
                }
            except Exception as exc:
                return {"error": str(exc)}

        return self.worker.run(_sta_get_sel)
