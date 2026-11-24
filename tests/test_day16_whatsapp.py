"""Day 16 Unit Tests — WhatsApp Desktop Voice & UI Automation Controller."""
import unittest
from unittest.mock import MagicMock, patch

from zye_windows.whatsapp_controller import WhatsAppController


class TestWhatsAppController(unittest.TestCase):
    def setUp(self):
        self.launcher = MagicMock()
        self.inspector = MagicMock()
        self.interaction = MagicMock()
        self.input_ctrl = MagicMock()
        self.window_mgr = MagicMock()

        self.whatsapp = WhatsAppController(
            launcher=self.launcher,
            inspector=self.inspector,
            interaction=self.interaction,
            input_ctrl=self.input_ctrl,
            window_mgr=self.window_mgr,
        )

    def test_open_whatsapp(self):
        self.launcher.open_any_app.return_value = {"status": "SUCCESS", "success": True}
        res = self.whatsapp.open_whatsapp()
        self.assertEqual(res["status"], "SUCCESS")
        self.launcher.open_any_app.assert_called_with("WhatsApp")

    def test_search_contact_empty(self):
        res = self.whatsapp.search_whatsapp_contact("")
        self.assertEqual(res["status"], "ERROR")

    def test_search_contact_single_match(self):
        self.window_mgr.manage_window.return_value = {"status": "SUCCESS"}
        self.interaction.click_ui_element.return_value = {"status": "SUCCESS"}
        self.inspector.inspect_app_ui.return_value = {
            "status": "SUCCESS",
            "controls": [
                {"name": "Arun Kumar", "control_type": "ListItem"}
            ]
        }
        res = self.whatsapp.search_whatsapp_contact("Arun")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["contact"], "Arun Kumar")
        self.assertTrue(res["verified"])

    def test_search_contact_ambiguous(self):
        self.window_mgr.manage_window.return_value = {"status": "SUCCESS"}
        self.interaction.click_ui_element.return_value = {"status": "SUCCESS"}
        self.inspector.inspect_app_ui.return_value = {
            "status": "SUCCESS",
            "controls": [
                {"name": "Arun Kumar", "control_type": "ListItem"},
                {"name": "Arun College", "control_type": "ListItem"},
            ]
        }
        res = self.whatsapp.search_whatsapp_contact("Arun")
        self.assertEqual(res["status"], "AMBIGUOUS_CONTACTS")
        self.assertEqual(len(res["candidates"]), 2)

    def test_search_contact_not_found(self):
        self.window_mgr.manage_window.return_value = {"status": "SUCCESS"}
        self.interaction.click_ui_element.return_value = {"status": "SUCCESS"}
        self.inspector.inspect_app_ui.return_value = {
            "status": "SUCCESS",
            "controls": []
        }
        res = self.whatsapp.search_whatsapp_contact("UnknownPerson")
        self.assertEqual(res["status"], "CONTACT_NOT_FOUND")

    def test_open_whatsapp_chat(self):
        with patch.object(self.whatsapp, "search_whatsapp_contact", return_value={"status": "SUCCESS", "contact": "Arun"}):
            self.interaction.click_ui_element.return_value = {"status": "SUCCESS"}
            res = self.whatsapp.open_whatsapp_chat("Arun")
            self.assertEqual(res["status"], "CHAT_OPENED")
            self.assertEqual(res["contact"], "Arun")

    def test_compose_whatsapp_message_draft(self):
        with patch.object(self.whatsapp, "open_whatsapp_chat", return_value={"status": "CHAT_OPENED", "contact": "Arun"}):
            self.interaction.click_ui_element.return_value = {"status": "SUCCESS"}
            self.input_ctrl.dictate_text_anywhere.return_value = {"status": "SUCCESS"}

            res = self.whatsapp.compose_whatsapp_message("Arun", "Naan 10 minutes-la call panren")
            self.assertEqual(res["status"], "DRAFTED")
            self.assertEqual(res["recipient"], "Arun")
            self.assertFalse(res["confirmed"])

    def test_send_whatsapp_message_unconfirmed_blocked(self):
        res = self.whatsapp.send_whatsapp_message("Arun", "Hello", confirmed=False)
        self.assertEqual(res["status"], "CONFIRMATION_REQUIRED")
        self.assertTrue(res["requires_user_confirmation"])

    def test_send_whatsapp_message_confirmed_success(self):
        with patch.object(self.whatsapp, "compose_whatsapp_message", return_value={"status": "DRAFTED", "recipient": "Arun", "message": "Hello"}):
            self.interaction.click_ui_element.return_value = {"status": "SUCCESS"}
            res = self.whatsapp.send_whatsapp_message("Arun", "Hello", confirmed=True)
            self.assertEqual(res["status"], "SUCCESS")
            self.assertTrue(res["confirmed"])

    def test_start_voice_call(self):
        with patch.object(self.whatsapp, "open_whatsapp_chat", return_value={"status": "CHAT_OPENED", "contact": "Arun"}):
            self.interaction.click_ui_element.return_value = {"status": "SUCCESS"}
            res = self.whatsapp.start_whatsapp_voice_call("Arun")
            self.assertEqual(res["status"], "SUCCESS")
            self.assertEqual(res["call_type"], "VOICE")

    def test_start_video_call(self):
        with patch.object(self.whatsapp, "open_whatsapp_chat", return_value={"status": "CHAT_OPENED", "contact": "Arun"}):
            self.interaction.click_ui_element.return_value = {"status": "SUCCESS"}
            res = self.whatsapp.start_whatsapp_video_call("Arun")
            self.assertEqual(res["status"], "SUCCESS")
            self.assertEqual(res["call_type"], "VIDEO")

    def test_end_call(self):
        self.interaction.click_ui_element.return_value = {"status": "SUCCESS"}
        res = self.whatsapp.end_whatsapp_call()
        self.assertEqual(res["status"], "SUCCESS")

    def test_get_call_status(self):
        self.inspector.inspect_app_ui.return_value = {"status": "SUCCESS", "controls": []}
        res = self.whatsapp.get_whatsapp_call_status()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertFalse(res["is_call_active"])


if __name__ == "__main__":
    unittest.main()
