"""
Day 19 Unit Tests — WhatsApp Desktop Voice Workflow Engine.
Verifies launching, contact search, contact disambiguation, chat opening,
message drafting, and explicit message send confirmation gates.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_windows.application_controller import WindowsApplicationController
from zye_windows.whatsapp_controller import WhatsAppController


class TestDay19WhatsAppWorkflow(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_whatsapp_ctrl = MagicMock()
        self.app_ctrl = WindowsApplicationController(whatsapp_ctrl=self.mock_whatsapp_ctrl)

    def test_open_whatsapp(self) -> None:
        """Verify open_whatsapp delegates to controller."""
        self.mock_whatsapp_ctrl.open_whatsapp.return_value = {
            "status": "LAUNCHED",
            "application": "WhatsApp",
            "verified": True,
        }
        res = self.app_ctrl.open_whatsapp()
        self.assertEqual(res.get("status"), "LAUNCHED")
        self.mock_whatsapp_ctrl.open_whatsapp.assert_called_once()

    def test_search_whatsapp_contact(self) -> None:
        """Verify contact search delegates to controller."""
        self.mock_whatsapp_ctrl.search_whatsapp_contact.return_value = {
            "status": "SUCCESS",
            "contact": "Arun",
            "matches": ["Arun Kumar"],
        }
        res = self.app_ctrl.search_whatsapp_contact("Arun")
        self.assertEqual(res.get("status"), "SUCCESS")
        self.mock_whatsapp_ctrl.search_whatsapp_contact.assert_called_once_with("Arun")

    def test_open_whatsapp_chat(self) -> None:
        """Verify open_whatsapp_chat delegates to controller."""
        self.mock_whatsapp_ctrl.open_whatsapp_chat.return_value = {
            "status": "SUCCESS",
            "contact": "Arun",
            "chat_open": True,
        }
        res = self.app_ctrl.open_whatsapp_chat("Arun")
        self.assertEqual(res.get("status"), "SUCCESS")
        self.mock_whatsapp_ctrl.open_whatsapp_chat.assert_called_once_with("Arun")

    def test_type_whatsapp_message_draft_only(self) -> None:
        """Verify type_whatsapp_message drafts text without sending."""
        self.mock_whatsapp_ctrl.type_whatsapp_message.return_value = {
            "status": "DRAFTED",
            "contact": "Arun",
            "message": "Naan 10 mins-la call panren",
        }
        res = self.app_ctrl.type_whatsapp_message("Arun", "Naan 10 mins-la call panren")
        self.assertEqual(res.get("status"), "DRAFTED")
        self.mock_whatsapp_ctrl.type_whatsapp_message.assert_called_once_with("Arun", "Naan 10 mins-la call panren")

    def test_send_whatsapp_message_unconfirmed_blocks_and_demands_confirmation(self) -> None:
        """Verify send_whatsapp_message with confirmed=False returns CONFIRMATION_REQUIRED."""
        res = self.app_ctrl.send_whatsapp_message("Arun", "Meeting starts now", confirmed=False)
        self.assertEqual(res.get("status"), "CONFIRMATION_REQUIRED")
        self.assertTrue(res.get("requires_confirmation"))
        self.assertEqual(res.get("recipient"), "Arun")
        self.assertEqual(res.get("message"), "Meeting starts now")
        self.mock_whatsapp_ctrl.send_whatsapp_message.assert_not_called()

    def test_send_whatsapp_message_confirmed_executes(self) -> None:
        """Verify send_whatsapp_message with confirmed=True dispatches send."""
        self.mock_whatsapp_ctrl.send_whatsapp_message.return_value = {
            "status": "SENT",
            "recipient": "Arun",
            "verified": True,
        }
        res = self.app_ctrl.send_whatsapp_message("Arun", "Meeting starts now", confirmed=True)
        self.assertEqual(res.get("status"), "SENT")
        self.mock_whatsapp_ctrl.send_whatsapp_message.assert_called_once_with("Arun", "Meeting starts now", confirmed=True)


if __name__ == "__main__":
    unittest.main()
