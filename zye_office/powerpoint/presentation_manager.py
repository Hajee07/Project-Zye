"""
Presentation Lifecycle Engine for Microsoft PowerPoint — Zye Day 23.
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from typing import Any, Dict, Optional
from zye_office.models import ConnectionPolicy
from zye_office.path_validator import OfficePathValidator
from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointCOMUnavailableError,
    PowerPointNoActivePresentationError,
)

logger = logging.getLogger("zye.office.powerpoint.presentation")


class PowerPointPresentationManager:
    """Manages presentation creation, opening, saving, and backup."""

    def __init__(
        self,
        adapter: Optional[PowerPointAdapter] = None,
        path_validator: Optional[OfficePathValidator] = None,
    ) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker
        self.path_validator = path_validator or OfficePathValidator()

    def create_presentation(self) -> Dict[str, Any]:
        """Create a new blank presentation."""
        def _sta_create() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            if app is None:
                self.adapter.connect(policy=ConnectionPolicy.AUTO_ATTACH_OR_LAUNCH)
                app = self.adapter.get_raw_app()
            if app is None:
                raise PowerPointCOMUnavailableError()

            pres = app.Presentations.Add()
            app.Visible = True
            name = getattr(pres, "Name", "Presentation1")
            return {
                "status": "SUCCESS",
                "presentation_name": name,
                "message": f"Successfully created fresh PowerPoint presentation '{name}'.",
            }

        return self.worker.run(_sta_create)

    def open_presentation(self, file_path: str, read_only: bool = False) -> Dict[str, Any]:
        """Open an existing presentation."""
        norm_path = self.path_validator.validate_path(file_path)
        if not os.path.exists(norm_path):
            raise FileNotFoundError(f"Presentation not found at: {norm_path}")

        def _sta_open() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            if app is None:
                self.adapter.connect(policy=ConnectionPolicy.AUTO_ATTACH_OR_LAUNCH)
                app = self.adapter.get_raw_app()
            if app is None:
                raise PowerPointCOMUnavailableError()

            pres = app.Presentations.Open(FileName=norm_path, ReadOnly=read_only)
            app.Visible = True
            return {
                "status": "SUCCESS",
                "presentation_name": getattr(pres, "Name", os.path.basename(norm_path)),
                "path": norm_path,
                "slide_count": pres.Slides.Count,
            }

        return self.worker.run(_sta_open)

    def save_presentation(self) -> Dict[str, Any]:
        """Save the active presentation."""
        def _sta_save() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            pres.Save()
            return {
                "status": "SUCCESS",
                "presentation_name": getattr(pres, "Name", "Untitled"),
                "is_saved": True,
            }

        return self.worker.run(_sta_save)

    def save_presentation_as(self, file_path: str, overwrite: bool = False) -> Dict[str, Any]:
        """Save presentation to a new destination."""
        norm_path = self.path_validator.validate_path(file_path)
        if os.path.exists(norm_path) and not overwrite:
            raise FileExistsError(f"Destination '{norm_path}' exists. Overwrite confirmation required.")

        def _sta_save_as() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            pres.SaveAs(FileName=norm_path)
            return {
                "status": "SUCCESS",
                "presentation_name": getattr(pres, "Name", os.path.basename(norm_path)),
                "path": norm_path,
                "is_saved": True,
            }

        return self.worker.run(_sta_save_as)

    def close_presentation(self, save_changes: bool = False) -> Dict[str, Any]:
        """Close the active presentation."""
        def _sta_close() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                return {"status": "SUCCESS", "message": "No active presentation to close."}

            name = getattr(pres, "Name", "Presentation")
            if save_changes:
                pres.Save()
            pres.Close()
            return {
                "status": "SUCCESS",
                "closed_presentation": name,
            }

        return self.worker.run(_sta_close)

    def create_presentation_backup(self) -> Dict[str, Any]:
        """Create a timestamped backup copy of current presentation."""
        def _sta_backup() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            orig_path = getattr(pres, "FullName", None)
            if not orig_path or not os.path.exists(orig_path):
                raise ValueError("Cannot backup unsaved in-memory presentation. Save it first.")

            dirname, filename = os.path.split(orig_path)
            base, ext = os.path.splitext(filename)
            backup_name = f"{base}_backup_{int(time.time())}{ext}"
            backup_path = os.path.join(dirname, backup_name)

            shutil.copy2(orig_path, backup_path)
            return {
                "status": "SUCCESS",
                "original_path": orig_path,
                "backup_path": backup_path,
            }

        return self.worker.run(_sta_backup)
