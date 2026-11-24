"""
Advanced Workbook Management Engine for Microsoft Excel — Zye Day 22.
Handles workbook creation, opening, saving, backups, protection checks, and external links.
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from typing import Any, Dict, List, Optional
from zye_office.excel.excel_adapter import ExcelAdapter
from zye_office.excel.excel_errors import (
    ExcelCOMUnavailableError,
    ExcelNoActiveWorkbookError,
    ExcelSecurityError,
    ExcelWorkbookProtectedError,
    ExcelWorkbookReadOnlyError,
)
from zye_office.excel.excel_metadata import ExcelMetadataExtractor
from zye_office.models import ConnectionPolicy
from zye_office.path_validator import OfficePathValidator

logger = logging.getLogger("zye.office.excel.workbook")


class ExcelWorkbookManager:
    """Manages Microsoft Excel workbook lifecycles and metadata."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        path_validator: Optional[OfficePathValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.path_validator = path_validator or OfficePathValidator()

    def create_workbook(self) -> Dict[str, Any]:
        """Create a fresh blank workbook in Excel."""
        def _sta_create() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            if app is None:
                self.adapter.connect(policy=ConnectionPolicy.AUTO_ATTACH_OR_LAUNCH)
                app = self.adapter.get_raw_app()
            if app is None:
                raise ExcelCOMUnavailableError()

            wb = app.Workbooks.Add()
            app.Visible = True
            wb_name = getattr(wb, "Name", "Workbook1")
            return {
                "status": "SUCCESS",
                "workbook_name": wb_name,
                "message": f"Successfully created fresh Excel workbook '{wb_name}'.",
            }

        return self.worker.run(_sta_create)

    def open_workbook(self, file_path: str, read_only: bool = False) -> Dict[str, Any]:
        """Open an existing Excel workbook safely."""
        norm_path = self.path_validator.validate_path(file_path)
        if not os.path.exists(norm_path):
            raise FileNotFoundError(f"Excel workbook not found at: {norm_path}")

        def _sta_open() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            if app is None:
                self.adapter.connect(policy=ConnectionPolicy.AUTO_ATTACH_OR_LAUNCH)
                app = self.adapter.get_raw_app()
            if app is None:
                raise ExcelCOMUnavailableError()

            wb = app.Workbooks.Open(Filename=norm_path, ReadOnly=read_only)
            app.Visible = True
            return {
                "status": "SUCCESS",
                "workbook_name": getattr(wb, "Name", os.path.basename(norm_path)),
                "path": norm_path,
                "is_read_only": getattr(wb, "ReadOnly", False),
            }

        return self.worker.run(_sta_open)

    def get_active_workbook_metadata(self) -> Dict[str, Any]:
        """Get structured metadata of currently focused workbook."""
        def _sta_meta() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            wb = self.adapter.get_active_workbook_raw()
            if wb is None:
                raise ExcelNoActiveWorkbookError()
            meta = ExcelMetadataExtractor.extract_workbook_metadata(app, wb)
            return meta.model_dump()

        return self.worker.run(_sta_meta)

    def save_workbook(self) -> Dict[str, Any]:
        """Save the active workbook."""
        def _sta_save() -> Dict[str, Any]:
            wb = self.adapter.get_active_workbook_raw()
            if wb is None:
                raise ExcelNoActiveWorkbookError()

            if getattr(wb, "ReadOnly", False):
                raise ExcelWorkbookReadOnlyError()

            wb.Save()
            return {
                "status": "SUCCESS",
                "workbook_name": getattr(wb, "Name", "Untitled"),
                "is_saved": True,
            }

        return self.worker.run(_sta_save)

    def save_workbook_as(self, file_path: str, overwrite: bool = False) -> Dict[str, Any]:
        """Save active workbook to a new file destination."""
        norm_path = self.path_validator.validate_path(file_path)
        if os.path.exists(norm_path) and not overwrite:
            raise ExcelSecurityError(
                f"Destination file '{norm_path}' already exists. Overwrite confirmation required.",
                error_code="EXCEL_CONFIRMATION_REQUIRED",
            )

        def _sta_save_as() -> Dict[str, Any]:
            wb = self.adapter.get_active_workbook_raw()
            if wb is None:
                raise ExcelNoActiveWorkbookError()

            wb.SaveAs(Filename=norm_path)
            return {
                "status": "SUCCESS",
                "workbook_name": getattr(wb, "Name", os.path.basename(norm_path)),
                "path": norm_path,
                "is_saved": True,
            }

        return self.worker.run(_sta_save_as)

    def close_workbook(self, save_changes: bool = False) -> Dict[str, Any]:
        """Close the active workbook."""
        def _sta_close() -> Dict[str, Any]:
            wb = self.adapter.get_active_workbook_raw()
            if wb is None:
                return {"status": "SUCCESS", "message": "No active workbook to close."}

            name = getattr(wb, "Name", "Workbook")
            wb.Close(SaveChanges=save_changes)
            return {
                "status": "SUCCESS",
                "closed_workbook": name,
                "saved": save_changes,
            }

        return self.worker.run(_sta_close)

    def create_workbook_backup(self) -> Dict[str, Any]:
        """Create an atomic timestamped backup copy of the current workbook."""
        def _sta_backup() -> Dict[str, Any]:
            wb = self.adapter.get_active_workbook_raw()
            if wb is None:
                raise ExcelNoActiveWorkbookError()

            orig_path = getattr(wb, "FullName", None)
            if not orig_path or not os.path.exists(orig_path):
                raise ExcelSecurityError("Cannot backup unsaved in-memory workbook. Save the workbook first.")

            dirname, filename = os.path.split(orig_path)
            base, ext = os.path.splitext(filename)
            backup_name = f"{base}_backup_{int(time.time())}{ext}"
            backup_path = os.path.join(dirname, backup_name)

            shutil.copy2(orig_path, backup_path)
            return {
                "status": "SUCCESS",
                "original_path": orig_path,
                "backup_path": backup_path,
                "backup_filename": backup_name,
            }

        return self.worker.run(_sta_backup)

    def get_workbook_external_links(self) -> Dict[str, Any]:
        """Detect any external linked workbooks or data connections."""
        def _sta_links() -> Dict[str, Any]:
            wb = self.adapter.get_active_workbook_raw()
            if wb is None:
                raise ExcelNoActiveWorkbookError()

            links = []
            try:
                # xlLinkTypeExcelLinks = 1
                link_sources = wb.LinkSources(1)
                if link_sources:
                    links = list(link_sources)
            except Exception:
                pass

            conn_names = []
            try:
                for c in wb.Connections:
                    conn_names.append(c.Name)
            except Exception:
                pass

            return {
                "status": "SUCCESS",
                "external_links_count": len(links),
                "external_links": links,
                "data_connections_count": len(conn_names),
                "data_connections": conn_names,
            }

        return self.worker.run(_sta_links)
