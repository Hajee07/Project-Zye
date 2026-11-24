"""
Universal Microsoft PowerPoint COM Adapter — Zye Day 23.
Dedicated STA thread-bound access to PowerPoint.Application COM interface.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.com_runtime import OfficeCOMRuntime
from zye_office.com_worker import STACOMWorker
from zye_office.models import ConnectionPolicy
from zye_office.models.day23_models import PowerPointPresentationMetadata
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointCOMUnavailableError,
    PowerPointNoActivePresentationError,
)
from zye_office.powerpoint.powerpoint_validator import PowerPointValidator

logger = logging.getLogger("zye.office.powerpoint.adapter")


class PowerPointAdapter:
    """Thread-safe COM Adapter for Microsoft PowerPoint executing on dedicated STA worker."""

    def __init__(
        self,
        com_runtime: Optional[OfficeCOMRuntime] = None,
        worker: Optional[STACOMWorker] = None,
        validator: Optional[PowerPointValidator] = None,
    ) -> None:
        self.worker = worker or STACOMWorker.get_instance()
        self.com_runtime = com_runtime or OfficeCOMRuntime(worker=self.worker)
        self.validator = validator or PowerPointValidator()

    def connect(
        self,
        policy: ConnectionPolicy = ConnectionPolicy.AUTO_ATTACH_OR_LAUNCH,
    ) -> Dict[str, Any]:
        """Establish or attach to live Microsoft PowerPoint COM application."""
        return self.com_runtime.connect_office_application("powerpoint", policy=policy)

    def attach_existing_powerpoint(self) -> Dict[str, Any]:
        return self.connect(policy=ConnectionPolicy.ATTACH_EXISTING)

    def launch_powerpoint(self) -> Dict[str, Any]:
        return self.connect(policy=ConnectionPolicy.LAUNCH_NEW)

    def is_running(self) -> bool:
        try:
            return self.get_raw_app() is not None
        except Exception:
            return False

    def disconnect(self, quit_if_created_by_zye: bool = False) -> Dict[str, Any]:
        return self.com_runtime.disconnect_office_application(
            "powerpoint",
            quit_if_created_by_zye=quit_if_created_by_zye,
        )

    def get_raw_app(self) -> Any:
        """INTERNAL: Access raw PowerPoint.Application COM dispatch inside STA worker."""
        return self.com_runtime.get_raw_com_object("powerpoint")

    def get_active_presentation_raw(self) -> Any:
        """INTERNAL: Retrieve active Presentation dispatch inside STA worker."""
        app = self.get_raw_app()
        if app is None:
            conn = self.connect(policy=ConnectionPolicy.ATTACH_EXISTING)
            if conn.get("status") != "SUCCESS":
                return None
            app = self.get_raw_app()

        if app is None:
            return None

        try:
            if getattr(app.Presentations, "Count", 0) > 0:
                return app.ActivePresentation
        except Exception as exc:
            logger.warning("Error accessing ActivePresentation in PowerPoint: %s", exc)
        return None

    def get_active_slide_raw(self) -> Any:
        """INTERNAL: Retrieve active Slide dispatch inside STA worker."""
        app = self.get_raw_app()
        if app is None:
            pres = self.get_active_presentation_raw()
            if pres is None:
                return None
            app = self.get_raw_app()
        try:
            return app.ActiveWindow.View.Slide
        except Exception:
            try:
                pres = self.get_active_presentation_raw()
                if pres and pres.Slides.Count > 0:
                    return pres.Slides(1)
            except Exception:
                pass
        return None

    def inspect_powerpoint_application(self) -> Dict[str, Any]:
        """Return structured metadata about PowerPoint and active presentation."""
        def _sta_inspect() -> Dict[str, Any]:
            app = self.get_raw_app()
            if app is None:
                conn = self.connect(policy=ConnectionPolicy.ATTACH_EXISTING)
                if conn.get("status") != "SUCCESS":
                    return conn
                app = self.get_raw_app()

            if app is None:
                raise PowerPointCOMUnavailableError()

            pres = None
            try:
                if app.Presentations.Count > 0:
                    pres = app.ActivePresentation
            except Exception:
                pass

            if pres is None:
                return PowerPointPresentationMetadata(
                    status="NO_ACTIVE_PRESENTATION",
                    message="PowerPoint is running, but no presentation is currently open.",
                ).model_dump()

            slide_count = pres.Slides.Count
            titles: List[str] = []
            for i in range(1, slide_count + 1):
                try:
                    s = pres.Slides(i)
                    if s.Shapes.HasTitle:
                        titles.append(s.Shapes.Title.TextFrame.TextRange.Text.strip())
                    else:
                        titles.append(f"Slide {i}")
                except Exception:
                    titles.append(f"Slide {i}")

            active_idx = 1
            active_title = titles[0] if titles else None
            try:
                active_s = app.ActiveWindow.View.Slide
                active_idx = active_s.SlideIndex
                active_title = titles[active_idx - 1] if active_idx <= len(titles) else None
            except Exception:
                pass

            name = getattr(pres, "Name", "Presentation1")
            try:
                full_path = getattr(pres, "FullName", None)
            except Exception:
                full_path = None

            return PowerPointPresentationMetadata(
                status="SUCCESS",
                presentation_name=name,
                filename=name,
                path=full_path,
                slide_count=slide_count,
                active_slide_index=active_idx,
                active_slide_title=active_title,
                slide_titles=titles,
                is_saved=getattr(pres, "Saved", True),
                is_read_only=getattr(pres, "ReadOnly", False),
                slide_width=getattr(pres.PageSetup, "SlideWidth", 960.0),
                slide_height=getattr(pres.PageSetup, "SlideHeight", 540.0),
            ).model_dump()

        return self.worker.run(_sta_inspect)

    def get_open_presentations(self) -> List[str]:
        """List filenames of all currently open presentations."""
        def _sta_get_pres() -> List[str]:
            app = self.get_raw_app()
            if app is None:
                return []
            names = []
            try:
                for p in app.Presentations:
                    names.append(p.Name)
            except Exception:
                pass
            return names

        return self.worker.run(_sta_get_pres)
