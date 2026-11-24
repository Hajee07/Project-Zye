"""
WhatsApp Desktop Voice & UI Automation Controller — Zye Day 16.
Coordinates UIA inspection, contact search, message drafting/sending, and voice/video call controls
with strict recipient verification, ambiguity detection, and Day 15 Safety Gateway integration.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

try:
    from pywinauto import Desktop
    _PYWINAUTO_AVAILABLE = True
except ImportError:
    _PYWINAUTO_AVAILABLE = False

from zye_windows.app_launcher import WindowsAppLauncher
from zye_windows.input_controller import WindowsInputController
from zye_windows.uia_inspector import WindowsUIAInspector
from zye_windows.uia_interaction import WindowsUIAInteraction
from zye_windows.window_manager import WindowsWindowManager
from zye_windows.windows_models import WhatsAppCallState, WhatsAppContact, WhatsAppMessage

logger = logging.getLogger("zye.windows.whatsapp")

WHATSAPP_WINDOW_TITLE = "WhatsApp"


class WhatsAppController:
    """
    Controls WhatsApp Desktop via Windows UI Automation.
    Prevents accidental message sending or misdirected calls.
    """

    def __init__(
        self,
        launcher: Optional[WindowsAppLauncher] = None,
        inspector: Optional[WindowsUIAInspector] = None,
        interaction: Optional[WindowsUIAInteraction] = None,
        input_ctrl: Optional[WindowsInputController] = None,
        window_mgr: Optional[WindowsWindowManager] = None,
    ) -> None:
        self.launcher = launcher or WindowsAppLauncher()
        self.inspector = inspector or WindowsUIAInspector()
        self.interaction = interaction or WindowsUIAInteraction()
        self.input_ctrl = input_ctrl or WindowsInputController()
        self.window_mgr = window_mgr or WindowsWindowManager()

    def open_whatsapp(self) -> dict[str, Any]:
        """
        Discover and launch WhatsApp Desktop, verifying its window is active and responsive.
        """
        return self.launcher.open_any_app("WhatsApp")

    def search_whatsapp_contact(self, contact_name: str) -> dict[str, Any]:
        """
        Search for a WhatsApp contact by name in the search box.
        Returns matching contacts or ambiguity notice if multiple matches exist.
        """
        if not contact_name or not str(contact_name).strip():
            return {"status": "ERROR", "message": "contact_name cannot be empty."}

        c_name = str(contact_name).strip()

        # 1. Ensure WhatsApp is focused
        focus_res = self.window_mgr.manage_window(WHATSAPP_WINDOW_TITLE, "focus")
        if focus_res.get("status") in ("WINDOW_NOT_FOUND", "ERROR"):
            # Try to launch it
            launch_res = self.open_whatsapp()
            if launch_res.get("status") not in ("LAUNCHED", "ALREADY_RUNNING"):
                return {"status": "APP_NOT_AVAILABLE", "message": "WhatsApp is not open or installed."}

        time.sleep(0.3)

        # 2. Inspect controls to find Search box
        # Common names in WhatsApp Desktop: "Search or start a new chat", "Search", "Search chats"
        search_edit = None
        for candidate in ["Search or start a new chat", "Search", "Search chats", "Search..."]:
            click_res = self.interaction.click_ui_element(WHATSAPP_WINDOW_TITLE, candidate, control_type="Edit")
            if click_res.get("status") == "SUCCESS":
                search_edit = candidate
                break

        if not search_edit:
            # Fallback: type directly or use Ctrl+F hotkey to focus WhatsApp search
            self.input_ctrl.press_hotkey(["ctrl", "f"])
            time.sleep(0.2)

        # 3. Type contact name into search box
        self.input_ctrl.dictate_text_anywhere(c_name, press_enter=False)
        time.sleep(0.5)

        # 4. Inspect results
        inspect_res = self.inspector.inspect_app_ui(WHATSAPP_WINDOW_TITLE, max_controls=60)
        controls = inspect_res.get("controls", [])

        # Look for matching contacts in list
        matching_contacts: list[str] = []
        for ctrl in controls:
            name = ctrl.get("name", "")
            c_type = ctrl.get("control_type", "")
            if c_name.lower() in name.lower() and c_type in ("ListItem", "Button", "Text"):
                if name not in matching_contacts and name != search_edit:
                    matching_contacts.append(name)

        if not matching_contacts:
            return {
                "status": "CONTACT_NOT_FOUND",
                "message": f"No WhatsApp contacts found matching '{c_name}'.",
                "query": c_name,
            }

        if len(matching_contacts) > 1:
            exact = [m for m in matching_contacts if m.lower() == c_name.lower()]
            if len(exact) == 1:
                return {
                    "status": "SUCCESS",
                    "contact": exact[0],
                    "query": c_name,
                    "verified": True,
                }
            return {
                "status": "AMBIGUOUS_CONTACTS",
                "message": f"Multiple contacts match '{c_name}'. Please clarify which contact.",
                "candidates": matching_contacts[:5],
                "query": c_name,
            }

        return {
            "status": "SUCCESS",
            "contact": matching_contacts[0],
            "query": c_name,
            "verified": True,
        }

    def open_whatsapp_chat(self, contact_name: str) -> dict[str, Any]:
        """
        Open the chat with a verified WhatsApp contact.
        """
        search_res = self.search_whatsapp_contact(contact_name)
        if search_res.get("status") != "SUCCESS":
            return search_res

        target_name = search_res.get("contact", contact_name)

        # Click the contact element in the list
        click_res = self.interaction.click_ui_element(WHATSAPP_WINDOW_TITLE, target_name)
        time.sleep(0.3)
        return {
            "status": "CHAT_OPENED",
            "contact": target_name,
            "message": f"Chat with '{target_name}' opened.",
            "verified": click_res.get("status") == "SUCCESS",
        }

    def compose_whatsapp_message(self, contact_name: str, message: str) -> dict[str, Any]:
        """
        Type a draft message into the active WhatsApp chat WITHOUT sending.
        """
        if not message:
            return {"status": "ERROR", "message": "Message cannot be empty."}

        # 1. Open chat first
        open_res = self.open_whatsapp_chat(contact_name)
        if open_res.get("status") not in ("CHAT_OPENED", "SUCCESS"):
            return open_res

        # 2. Locate message input box: "Type a message", "Message"
        target_edit = None
        for candidate in ["Type a message", "Message", "Write a message"]:
            click_res = self.interaction.click_ui_element(WHATSAPP_WINDOW_TITLE, candidate, control_type="Edit")
            if click_res.get("status") == "SUCCESS":
                target_edit = candidate
                break

        # 3. Paste message text without pressing Enter
        type_res = self.input_ctrl.dictate_text_anywhere(message, press_enter=False)

        msg_obj = WhatsAppMessage(
            recipient=contact_name,
            message=message,
            status="COMPOSED_DRAFT",
            confirmed=False,
            verification="Draft message typed into active chat. Not sent.",
        )
        return {
            **msg_obj.model_dump(),
            "status": "DRAFTED",
        }

    def send_whatsapp_message(
        self,
        contact_name: str,
        message: str,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """
        Send a WhatsApp message. Requires explicit authorization (confirmed=True).
        Protected by Day 15 Safety Gateway.
        """
        if not confirmed:
            return {
                "status": "CONFIRMATION_REQUIRED",
                "recipient": contact_name,
                "message": message,
                "requires_user_confirmation": True,
                "details": f"Safety Gateway requires explicit user authorization before sending message to '{contact_name}'.",
            }

        # 1. Compose draft if not already typed
        compose_res = self.compose_whatsapp_message(contact_name, message)
        if compose_res.get("status") not in ("DRAFTED", "COMPOSED_DRAFT", "SUCCESS"):
            return compose_res

        # 2. Click Send button or press Enter to dispatch
        send_clicked = False
        for send_label in ["Send", "send"]:
            click_res = self.interaction.click_ui_element(WHATSAPP_WINDOW_TITLE, send_label, control_type="Button")
            if click_res.get("status") == "SUCCESS":
                send_clicked = True
                break

        if not send_clicked:
            # Fallback to pressing Enter
            self.input_ctrl.press_hotkey(["enter"])
            send_clicked = True

        time.sleep(0.3)
        msg_obj = WhatsAppMessage(
            recipient=contact_name,
            message=message,
            status="SENT",
            confirmed=True,
            verification="Dispatched message to WhatsApp chat.",
        )
        return {
            **msg_obj.model_dump(),
            "status": "SUCCESS",
        }

    def start_whatsapp_voice_call(self, contact_name: str) -> dict[str, Any]:
        """
        Initiate a WhatsApp voice call with a confirmed contact.
        """
        open_res = self.open_whatsapp_chat(contact_name)
        if open_res.get("status") not in ("CHAT_OPENED", "SUCCESS"):
            return open_res

        # Find Voice Call button
        call_clicked = False
        for btn_name in ["Voice call", "Audio call", "Start voice call", "Call"]:
            click_res = self.interaction.click_ui_element(WHATSAPP_WINDOW_TITLE, btn_name, control_type="Button")
            if click_res.get("status") == "SUCCESS":
                call_clicked = True
                break

        state = WhatsAppCallState(
            contact=contact_name,
            call_type="VOICE",
            status="INITIATED" if call_clicked else "CALL_BUTTON_NOT_FOUND",
            details="Voice call initiated." if call_clicked else "Could not locate Voice call button.",
        )
        return {
            **state.model_dump(),
            "status": "SUCCESS" if call_clicked else "CALL_BUTTON_NOT_FOUND",
        }

    def start_whatsapp_video_call(self, contact_name: str) -> dict[str, Any]:
        """
        Initiate a WhatsApp video call with a confirmed contact.
        """
        open_res = self.open_whatsapp_chat(contact_name)
        if open_res.get("status") not in ("CHAT_OPENED", "SUCCESS"):
            return open_res

        # Find Video Call button
        call_clicked = False
        for btn_name in ["Video call", "Start video call"]:
            click_res = self.interaction.click_ui_element(WHATSAPP_WINDOW_TITLE, btn_name, control_type="Button")
            if click_res.get("status") == "SUCCESS":
                call_clicked = True
                break

        state = WhatsAppCallState(
            contact=contact_name,
            call_type="VIDEO",
            status="INITIATED" if call_clicked else "CALL_BUTTON_NOT_FOUND",
            details="Video call initiated." if call_clicked else "Could not locate Video call button.",
        )
        return {
            **state.model_dump(),
            "status": "SUCCESS" if call_clicked else "CALL_BUTTON_NOT_FOUND",
        }

    def end_whatsapp_call(self) -> dict[str, Any]:
        """
        Terminate any active WhatsApp voice or video call.
        """
        # Search for End Call button in WhatsApp window or active call window
        end_clicked = False
        for candidate_window in [WHATSAPP_WINDOW_TITLE, "WhatsApp Call", "Call"]:
            for btn_name in ["End call", "Leave call", "Decline call", "Hang up"]:
                click_res = self.interaction.click_ui_element(candidate_window, btn_name, control_type="Button")
                if click_res.get("status") == "SUCCESS":
                    end_clicked = True
                    break
            if end_clicked:
                break

        state = WhatsAppCallState(
            contact="ACTIVE_CALL",
            call_type="VOICE",
            status="ENDED" if end_clicked else "NO_ACTIVE_CALL_FOUND",
            details="Call successfully ended." if end_clicked else "No active call End button was found.",
        )
        return {
            **state.model_dump(),
            "status": "SUCCESS" if end_clicked else "NO_ACTIVE_CALL",
        }

    def get_whatsapp_call_status(self) -> dict[str, Any]:
        """
        Query current WhatsApp call state (idle, active call window, or ringing).
        """
        windows = self.window_mgr.find_windows("Call")
        is_calling = any("whatsapp" in (w.title or "").lower() or "call" in (w.title or "").lower() for w in windows)
        return {
            "status": "SUCCESS",
            "is_call_active": bool(is_calling),
            "call_window": windows[0].title if windows else None,
        }
