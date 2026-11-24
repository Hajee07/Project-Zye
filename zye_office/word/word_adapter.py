"""
Microsoft Word COM Application Adapter — Zye Day 21.
Provides a unified, thread-safe gateway to the live Word.Application instance
executing strictly within the dedicated STA COM worker.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from zye_office.com_runtime import OfficeCOMRuntime
from zye_office.com_worker import STACOMWorker, get_shared_sta_worker
from zye_office.models import ConnectionPolicy, OfficeAppType
from zye_office.word.word_errors import (
    WordNoActiveDocumentError,
    WordNotInstalledError,
    format_word_error,
)
from zye_office.word.word_validator import WordValidator

logger = logging.getLogger("zye.office.word.adapter")


class WordAdapter:
    """
    Manages live COM connection to Microsoft Word, active document references,
    and dispatches operations to the dedicated STA COM worker.
    """

    PROG_ID = "Word.Application"

    def __init__(
        self,
        com_runtime: Optional[OfficeCOMRuntime] = None,
        worker: Optional[STACOMWorker] = None,
        validator: Optional[WordValidator] = None,
    ) -> None:
        self.worker = worker or get_shared_sta_worker()
        self.com_runtime = com_runtime or OfficeCOMRuntime(worker=self.worker)
        self.validator = validator or WordValidator()

    def connect(
        self,
        policy: ConnectionPolicy = ConnectionPolicy.ATTACH_EXISTING,
    ) -> Dict[str, Any]:
        """Establish or attach to live Microsoft Word COM application."""
        return self.com_runtime.connect_office_application("word", policy=policy)

    def is_running(self) -> bool:
        """Check if Word COM application is reachable or running."""
        try:
            return self.get_raw_app() is not None
        except Exception:
            return False

    def disconnect(self, quit_if_created_by_zye: bool = False) -> Dict[str, Any]:
        """Release COM references and optionally quit if created by Zye."""
        return self.com_runtime.disconnect_office_application(
            "word",
            quit_if_created_by_zye=quit_if_created_by_zye,
        )

    def get_raw_app(self) -> Any:
        """INTERNAL: Access raw Word.Application COM dispatch inside STA worker."""
        return self.com_runtime.get_raw_com_object("word")

    def get_active_document_raw(self) -> Any:
        """INTERNAL: Retrieve active Document object inside STA worker."""
        app = self.get_raw_app()
        if app is None:
            # Auto-connect if attached
            conn = self.connect(policy=ConnectionPolicy.ATTACH_EXISTING)
            if conn.get("status") != "SUCCESS":
                return None
            app = self.get_raw_app()

        if app is None:
            return None

        try:
            if app.Documents.Count > 0:
                return app.ActiveDocument
        except Exception as exc:
            logger.warning("Error accessing ActiveDocument in Word: %s", exc)
        return None

    def create_document(self) -> Dict[str, Any]:
        """Create a fresh blank document in Microsoft Word."""
        def _sta_create() -> Dict[str, Any]:
            app = self.get_raw_app()
            if app is None:
                self.connect(policy=ConnectionPolicy.AUTO_ATTACH_OR_LAUNCH)
                app = self.get_raw_app()
            if app is None:
                raise WordNotInstalledError("Could not connect to or launch Word.Application.")

            doc = app.Documents.Add()
            app.Visible = True
            return {
                "status": "SUCCESS",
                "document_name": doc.Name,
                "created": True,
                "message": f"Created new blank Word document '{doc.Name}'.",
            }

        return self.worker.run(_sta_create)

    def open_document(self, file_path: str, read_only: bool = False) -> Dict[str, Any]:
        """Open an existing Word document by canonical path."""
        canonical_path = self.validator.path_validator.validate_path(file_path, must_exist=True)

        def _sta_open() -> Dict[str, Any]:
            app = self.get_raw_app()
            if app is None:
                self.connect(policy=ConnectionPolicy.AUTO_ATTACH_OR_LAUNCH)
                app = self.get_raw_app()
            if app is None:
                raise WordNotInstalledError("Could not connect to or launch Word.Application.")

            doc = app.Documents.Open(FileName=canonical_path, ReadOnly=read_only)
            app.Visible = True
            return {
                "status": "SUCCESS",
                "document_name": doc.Name,
                "path": canonical_path,
                "read_only": read_only,
                "message": f"Successfully opened document '{doc.Name}'.",
            }

        return self.worker.run(_sta_open)

    def save_document(self, path: Optional[str] = None) -> Dict[str, Any]:
        """Save the currently active document to its existing path or new path."""
        def _sta_save() -> Dict[str, Any]:
            doc = self.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            if path:
                canonical = self.validator.path_validator.validate_path(path)
                doc.SaveAs2(FileName=canonical)
                saved_to = canonical
            else:
                doc.Save()
                saved_to = getattr(doc, "FullName", doc.Name)

            return {
                "status": "SUCCESS",
                "document_name": doc.Name,
                "saved_path": saved_to,
                "message": f"Document '{doc.Name}' saved successfully.",
            }

        return self.worker.run(_sta_save)

    def save_document_as(self, file_path: str, format_type: int = 16) -> Dict[str, Any]:
        """Save active document under a new path with specific format (default .docx)."""
        canonical_path = self.validator.path_validator.validate_path(file_path)

        def _sta_save_as() -> Dict[str, Any]:
            doc = self.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            doc.SaveAs2(FileName=canonical_path, FileFormat=format_type)
            return {
                "status": "SUCCESS",
                "document_name": doc.Name,
                "saved_path": canonical_path,
                "message": f"Document saved as '{canonical_path}'.",
            }

        return self.worker.run(_sta_save_as)

    def close_document(self, save_changes: bool = False) -> Dict[str, Any]:
        """Close the currently active document."""
        def _sta_close() -> Dict[str, Any]:
            doc = self.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            name = doc.Name
            doc.Close(SaveChanges=save_changes)
            return {
                "status": "SUCCESS",
                "closed_document": name,
                "saved": save_changes,
                "message": f"Document '{name}' closed.",
            }

        return self.worker.run(_sta_close)
