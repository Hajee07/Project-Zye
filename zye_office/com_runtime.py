"""
Windows Live COM Runtime Engine — Zye Day 20.
Handles COM connection policies (ATTACH_EXISTING, LAUNCH_NEW, AUTO_ATTACH_OR_LAUNCH),
attaches to running Office applications via GetActiveObject, dispatches new instances,
and maintains thread-safe COM object handles inside the STA worker.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Any, Optional

from zye_office.app_registry import OfficeAppRegistry
from zye_office.com_worker import STACOMWorker, run_on_sta_worker
from zye_office.errors import (
    COMAppUnavailableError,
    COMDisconnectedError,
    COMInitializationError,
    format_office_error,
)
from zye_office.models import ConnectionPolicy, OfficeAppType

logger = logging.getLogger("zye.office.com_runtime")


class OfficeCOMRuntime:
    """
    Manages live Windows COM application lifecycles, active object attachment,
    and COM instance storage inside the dedicated STA thread.
    """

    def __init__(
        self,
        app_registry: Optional[OfficeAppRegistry] = None,
        worker: Optional[STACOMWorker] = None,
    ) -> None:
        self.app_registry = app_registry or OfficeAppRegistry()
        self.worker = worker or STACOMWorker.get_instance()
        # Internal map of active COM references: key -> COM dispatch object
        # NOTE: This dictionary is ONLY read/written inside the STA worker thread!
        self._sta_com_objects: dict[str, Any] = {}
        self._created_by_zye: dict[str, bool] = {}

    def get_app_instance(self, session_id_or_app: str) -> Any:
        """Alias for get_raw_com_object supporting app name or session ID."""
        norm = (session_id_or_app or "").lower().strip()
        if norm in self._sta_com_objects:
            return self._sta_com_objects[norm]
        # If session_id formatted e.g. sess_word_..., extract app
        for k in ("word", "excel", "powerpoint", "outlook"):
            if k in norm and k in self._sta_com_objects:
                return self._sta_com_objects[k]
        return None

    def _sta_get_active_object(self, prog_id: str) -> Any:
        """Call win32com.client.GetActiveObject inside STA thread."""
        import win32com.client
        return win32com.client.GetActiveObject(prog_id)

    def _sta_dispatch(self, prog_id: str) -> Any:
        """Call win32com.client.Dispatch inside STA thread."""
        import win32com.client
        app = win32com.client.Dispatch(prog_id)
        # Make visible where supported
        try:
            if hasattr(app, "Visible"):
                app.Visible = True
        except Exception:
            pass
        return app

    def connect_office_application(
        self,
        app_name: str,
        policy: ConnectionPolicy = ConnectionPolicy.ATTACH_EXISTING,
    ) -> dict[str, Any]:
        """
        Connect to an Office application according to the specified ConnectionPolicy.
        Executes on STA worker thread and returns connection metadata.
        """
        prog_id = self.app_registry.get_office_prog_id(app_name)
        if not prog_id:
            return format_office_error(
                error_code="COM_APPLICATION_NOT_REGISTERED",
                message=f"Unknown or unsupported Office application '{app_name}'.",
                app_name=app_name,
            )

        norm_app = app_name.lower().strip()

        def _sta_connect() -> dict[str, Any]:
            com_obj = None
            connected_via = ""
            created_new = False

            # Check if we already hold an active, valid COM pointer
            existing_ref = self._sta_com_objects.get(norm_app)
            if existing_ref is not None:
                try:
                    # Ping COM object property to verify responsiveness
                    _ = getattr(existing_ref, "Name", None) or getattr(existing_ref, "Version", None)
                    return {
                        "status": "SUCCESS",
                        "app_name": norm_app,
                        "prog_id": prog_id,
                        "connection_type": "REUSED_SESSION",
                        "created_by_zye": self._created_by_zye.get(norm_app, False),
                        "message": f"Reused active COM reference for '{norm_app}'.",
                    }
                except Exception:
                    # Disconnected reference; purge it
                    self._sta_com_objects.pop(norm_app, None)

            # Strategy: ATTACH_EXISTING or AUTO_ATTACH
            if policy in (ConnectionPolicy.ATTACH_EXISTING, ConnectionPolicy.AUTO_ATTACH_OR_LAUNCH, ConnectionPolicy.INSPECT_ONLY):
                try:
                    com_obj = self._sta_get_active_object(prog_id)
                    connected_via = "ATTACH_EXISTING"
                    created_new = False
                    logger.info("Successfully attached to running Office application: %s", prog_id)
                except Exception as attach_exc:
                    if policy in (ConnectionPolicy.ATTACH_EXISTING, ConnectionPolicy.INSPECT_ONLY):
                        return format_office_error(
                            error_code="OFFICE_APP_NOT_RUNNING",
                            message=f"{norm_app.title()} is not currently open or running (GetActiveObject returned: {attach_exc}).",
                            app_name=norm_app,
                            remediation="Launch the application manually or use ConnectionPolicy.AUTO_ATTACH_OR_LAUNCH.",
                        )

            # Strategy: LAUNCH_NEW or AUTO_ATTACH fallback
            if com_obj is None and policy in (ConnectionPolicy.LAUNCH_NEW, ConnectionPolicy.AUTO_ATTACH_OR_LAUNCH):
                try:
                    com_obj = self._sta_dispatch(prog_id)
                    connected_via = "LAUNCH_NEW"
                    created_new = True
                    logger.info("Successfully launched new Office application instance: %s", prog_id)
                except Exception as launch_exc:
                    return format_office_error(
                        error_code="COM_APPLICATION_UNAVAILABLE",
                        message=f"Failed to launch '{norm_app}' via COM Dispatch: {launch_exc}",
                        app_name=norm_app,
                    )

            if com_obj is None:
                return format_office_error(
                    error_code="COM_CONNECTION_FAILED",
                    message=f"Could not connect to '{norm_app}' under policy '{policy.value}'.",
                    app_name=norm_app,
                )

            # Store COM object in worker dictionary
            self._sta_com_objects[norm_app] = com_obj
            self._created_by_zye[norm_app] = created_new

            # Extract basic version
            ver = None
            try:
                ver = str(getattr(com_obj, "Version", ""))
            except Exception:
                pass

            return {
                "status": "SUCCESS",
                "app_name": norm_app,
                "prog_id": prog_id,
                "connection_type": connected_via,
                "version": ver,
                "created_by_zye": created_new,
                "message": f"Successfully connected to {norm_app.title()} ({connected_via}).",
            }

        return self.worker.run(_sta_connect)

    def attach_existing_office_application(self, app_name: str) -> dict[str, Any]:
        """Convenience method to attach to already running Office instance."""
        return self.connect_office_application(app_name, policy=ConnectionPolicy.ATTACH_EXISTING)

    def launch_office_application(self, app_name: str) -> dict[str, Any]:
        """Convenience method to launch a new Office application instance."""
        return self.connect_office_application(app_name, policy=ConnectionPolicy.LAUNCH_NEW)

    def verify_office_connection(self, app_name: str) -> dict[str, Any]:
        """Verify that the COM connection to app_name is active and responsive."""
        norm_app = app_name.lower().strip()

        def _sta_verify() -> dict[str, Any]:
            com_obj = self._sta_com_objects.get(norm_app)
            if com_obj is None:
                return {
                    "status": "NOT_CONNECTED",
                    "app_name": norm_app,
                    "is_connected": False,
                    "message": f"No active COM session for '{norm_app}'.",
                }
            try:
                name_val = getattr(com_obj, "Name", norm_app)
                return {
                    "status": "CONNECTED",
                    "app_name": norm_app,
                    "is_connected": True,
                    "name": str(name_val),
                }
            except Exception as exc:
                # Dead pointer
                self._sta_com_objects.pop(norm_app, None)
                return {
                    "status": "DISCONNECTED",
                    "app_name": norm_app,
                    "is_connected": False,
                    "message": f"COM pointer disconnected: {exc}",
                }

        return self.worker.run(_sta_verify)

    def disconnect_office_application(self, app_name: str, quit_if_created_by_zye: bool = False) -> dict[str, Any]:
        """
        Safely release COM references. If quit_if_created_by_zye is True and Zye spawned the app,
        gracefully invokes Quit().
        """
        norm_app = app_name.lower().strip()

        def _sta_disconnect() -> dict[str, Any]:
            com_obj = self._sta_com_objects.pop(norm_app, None)
            created = self._created_by_zye.pop(norm_app, False)
            if com_obj is None:
                return {
                    "status": "SUCCESS",
                    "app_name": norm_app,
                    "message": f"'{norm_app}' was not connected.",
                }
            quitted = False
            if quit_if_created_by_zye and created:
                try:
                    if hasattr(com_obj, "Quit"):
                        com_obj.Quit()
                        quitted = True
                except Exception as exc:
                    logger.warning("Error quitting %s: %s", norm_app, exc)

            # Explicitly release reference in COM
            del com_obj
            return {
                "status": "SUCCESS",
                "app_name": norm_app,
                "quitted": quitted,
                "message": f"Disconnected from {norm_app.title()}.",
            }

        return self.worker.run(_sta_disconnect)

    def get_raw_com_object(self, app_name: str) -> Any:
        """
        INTERNAL USE ONLY inside STA worker: Retrieve the raw COM object for an app.
        Caller MUST ensure this is only called from within the STA worker thread.
        """
        norm_app = app_name.lower().strip()
        return self._sta_com_objects.get(norm_app)
