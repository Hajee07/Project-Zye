"""
Sequential Application Controller & WhatsApp Workflow Engine — Zye Day 19.
Coordinates App Catalog, Process Manager, Window Manager, UI Automation, and Input Controller,
and provides multi-step WhatsApp voice workflows with strict confirmation gates.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Any, Optional

from zye_windows.app_catalog import WindowsAppCatalog
from zye_windows.input_controller import WindowsInputController
from zye_windows.process_manager import WindowsProcessManager
from zye_windows.ui_automation import WindowsUIAutomation
from zye_windows.whatsapp_controller import WhatsAppController
from zye_windows.window_manager import WindowsWindowManager

logger = logging.getLogger("zye.windows.application_controller")


class WindowsApplicationController:
    """
    Central coordinator for desktop application workflows, sequential multi-step commands,
    and voice-directed WhatsApp messaging and call controls.
    """

    def __init__(
        self,
        app_catalog: Optional[WindowsAppCatalog] = None,
        process_mgr: Optional[WindowsProcessManager] = None,
        window_mgr: Optional[WindowsWindowManager] = None,
        ui_auto: Optional[WindowsUIAutomation] = None,
        input_ctrl: Optional[WindowsInputController] = None,
        whatsapp_ctrl: Optional[WhatsAppController] = None,
    ) -> None:
        self.app_catalog = app_catalog or WindowsAppCatalog()
        self.process_mgr = process_mgr or WindowsProcessManager()
        self.window_mgr = window_mgr or WindowsWindowManager()
        self.ui_auto = ui_auto or WindowsUIAutomation()
        self.input_ctrl = input_ctrl or WindowsInputController()
        self.whatsapp_ctrl = whatsapp_ctrl or WhatsAppController(
            input_ctrl=self.input_ctrl,
            window_mgr=self.window_mgr,
        )
        self._current_workflow: dict[str, Any] = {}

    # =========================================================================
    # Universal Application Controls
    # =========================================================================

    def open_application(self, app_name: str) -> dict[str, Any]:
        """
        Open or bring to foreground a Windows application by name.
        Verifies emergence of the application window.
        """
        if not app_name or not str(app_name).strip():
            return {"status": "ERROR", "message": "Application name cannot be empty."}

        clean = str(app_name).strip()
        launch_res = self.app_catalog.launch_application(clean)
        self._current_workflow = {
            "app_name": clean,
            "last_action": "open_application",
            "launch_result": launch_res,
            "timestamp": time.time(),
        }
        return launch_res

    def inspect_application(self, app_name: str) -> dict[str, Any]:
        """Inspect available controls and accessible fields for the specified application."""
        if not app_name:
            return {"status": "ERROR", "message": "Application name cannot be empty."}
        return self.ui_auto.inspect_app_ui(str(app_name).strip())

    def search_inside_application(self, app_name: str, query: str) -> dict[str, Any]:
        """
        Locate search input field in application, focus it, and insert query.
        """
        clean_app = str(app_name).strip()
        clean_q = str(query).strip()
        if not clean_app or not clean_q:
            return {"status": "ERROR", "message": "app_name and query cannot be empty."}

        # Check for search field candidates
        for field_name in ["Search", "Find", "Search or enter address", "Search or start a new chat"]:
            found = self.ui_auto.find_ui_element(clean_app, field_name, control_type="Edit")
            if found.get("status") == "SUCCESS":
                self.ui_auto.click_ui_element(clean_app, field_name, control_type="Edit")
                return self.input_ctrl.dictate_text_anywhere(clean_q, press_enter=True)

        # Fallback: send standard Ctrl+F or Ctrl+E hotkey
        self.window_mgr.focus_window(clean_app)
        self.input_ctrl.press_key("ctrl+f")
        time.sleep(0.2)
        return self.input_ctrl.dictate_text_anywhere(clean_q, press_enter=True)

    def click_application_control(self, app_name: str, control_name: str) -> dict[str, Any]:
        """Safely click an interactive UI control within the target application."""
        return self.ui_auto.click_ui_element(app_name, control_name)

    def type_application_text(self, app_name: str, field_name: str, text: str) -> dict[str, Any]:
        """Insert Unicode or English text into an Edit control inside the application."""
        return self.ui_auto.type_into_ui_element(app_name, field_name, text, submit=False)

    def close_application_window(self, app_name: str) -> dict[str, Any]:
        """Close an application's top-level window gracefully."""
        if not app_name:
            return {"status": "ERROR", "message": "Application name cannot be empty."}
        return self.window_mgr.manage_window(str(app_name).strip(), "close")

    def get_application_status(self, app_name: str) -> dict[str, Any]:
        """
        Check if application is running, find its PID and responsive windows.
        """
        clean = str(app_name).strip()
        procs = self.process_mgr.find_process_by_name(clean)
        wins = self.window_mgr.find_windows(clean)
        return {
            "status": "SUCCESS",
            "application": clean,
            "is_running": len(procs) > 0,
            "process_count": len(procs),
            "processes": procs[:5],
            "window_count": len(wins),
            "has_open_window": len(wins) > 0,
        }

    # =========================================================================
    # WhatsApp Desktop Workflows & Confirmation Gates
    # =========================================================================

    def open_whatsapp(self) -> dict[str, Any]:
        """Launch or focus WhatsApp Desktop."""
        return self.whatsapp_ctrl.open_whatsapp()

    def inspect_whatsapp_ui(self) -> dict[str, Any]:
        """Inspect WhatsApp Desktop UI elements."""
        return self.whatsapp_ctrl.inspect_whatsapp_ui()

    def search_whatsapp_contact(self, contact_name: str) -> dict[str, Any]:
        """Search for a contact inside WhatsApp Desktop."""
        return self.whatsapp_ctrl.search_whatsapp_contact(contact_name)

    def open_whatsapp_chat(self, contact_name: str) -> dict[str, Any]:
        """Open conversation with verified contact in WhatsApp Desktop."""
        return self.whatsapp_ctrl.open_whatsapp_chat(contact_name)

    def type_whatsapp_message(self, contact_name: str, message: str) -> dict[str, Any]:
        """Draft a message into the WhatsApp message input box without sending."""
        return self.whatsapp_ctrl.type_whatsapp_message(contact_name, message)

    def send_whatsapp_message(
        self,
        contact_name: str,
        message: str,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """
        Send a WhatsApp message with strict two-stage confirmation gate.
        If confirmed=False, returns message details requiring explicit user approval.
        """
        if not contact_name or not message:
            return {"status": "ERROR", "message": "contact_name and message cannot be empty."}

        if not confirmed:
            return {
                "status": "CONFIRMATION_REQUIRED",
                "recipient": contact_name,
                "message": message,
                "warning": f"Please confirm: Do you want to send this message to '{contact_name}'?",
                "requires_confirmation": True,
            }

        return self.whatsapp_ctrl.send_whatsapp_message(contact_name, message, confirmed=True)

    def start_whatsapp_voice_call(
        self,
        contact_name: str,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """
        Initiate a WhatsApp voice call with confirmation gate.
        """
        if not contact_name:
            return {"status": "ERROR", "message": "contact_name cannot be empty."}

        if not confirmed:
            return {
                "status": "CONFIRMATION_REQUIRED",
                "recipient": contact_name,
                "call_type": "VOICE",
                "warning": f"Please confirm: Do you want to place a voice call to '{contact_name}'?",
                "requires_confirmation": True,
            }

        return self.whatsapp_ctrl.start_whatsapp_call(contact_name, call_type="voice")

    def start_whatsapp_video_call(
        self,
        contact_name: str,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """
        Initiate a WhatsApp video call with confirmation gate.
        """
        if not contact_name:
            return {"status": "ERROR", "message": "contact_name cannot be empty."}

        if not confirmed:
            return {
                "status": "CONFIRMATION_REQUIRED",
                "recipient": contact_name,
                "call_type": "VIDEO",
                "warning": f"Please confirm: Do you want to place a video call to '{contact_name}'?",
                "requires_confirmation": True,
            }

        return self.whatsapp_ctrl.start_whatsapp_call(contact_name, call_type="video")

    def end_whatsapp_call(self) -> dict[str, Any]:
        """End an active WhatsApp call."""
        return self.whatsapp_ctrl.end_whatsapp_call()

    def get_whatsapp_call_status(self) -> dict[str, Any]:
        """Get current call status and active call window info."""
        return self.whatsapp_ctrl.get_call_status()
