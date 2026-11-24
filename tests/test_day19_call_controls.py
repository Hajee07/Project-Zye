"""
Day 19 Unit Tests — WhatsApp Call Controls & Confirmation Safety.
Verifies voice and video call discovery, initiation confirmation gates,
active call inspection, and end call termination.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_windows.application_controller import WindowsApplicationController


class TestDay19CallControls(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_whatsapp_ctrl = MagicMock()
        self.app_ctrl = WindowsApplicationController(whatsapp_ctrl=self.mock_whatsapp_ctrl)

    def test_start_voice_call_unconfirmed_blocks(self) -> None:
        """Verify starting voice call without confirmation returns CONFIRMATION_REQUIRED."""
        res = self.app_ctrl.start_whatsapp_voice_call("Arun", confirmed=False)
        self.assertEqual(res.get("status"), "CONFIRMATION_REQUIRED")
        self.assertEqual(res.get("call_type"), "VOICE")
        self.assertTrue(res.get("requires_confirmation"))
        self.mock_whatsapp_ctrl.start_whatsapp_call.assert_not_called()

    def test_start_voice_call_confirmed_executes(self) -> None:
        """Verify starting voice call with confirmed=True proceeds."""
        self.mock_whatsapp_ctrl.start_whatsapp_call.return_value = {
            "status": "CALLING",
            "contact": "Arun",
            "call_type": "voice",
        }
        res = self.app_ctrl.start_whatsapp_voice_call("Arun", confirmed=True)
        self.assertEqual(res.get("status"), "CALLING")
        self.mock_whatsapp_ctrl.start_whatsapp_call.assert_called_once_with("Arun", call_type="voice")

    def test_start_video_call_unconfirmed_blocks(self) -> None:
        """Verify starting video call without confirmation returns CONFIRMATION_REQUIRED."""
        res = self.app_ctrl.start_whatsapp_video_call("Arun", confirmed=False)
        self.assertEqual(res.get("status"), "CONFIRMATION_REQUIRED")
        self.assertEqual(res.get("call_type"), "VIDEO")
        self.assertTrue(res.get("requires_confirmation"))
        self.mock_whatsapp_ctrl.start_whatsapp_call.assert_not_called()

    def test_start_video_call_confirmed_executes(self) -> None:
        """Verify starting video call with confirmed=True proceeds."""
        self.mock_whatsapp_ctrl.start_whatsapp_call.return_value = {
            "status": "CALLING",
            "contact": "Arun",
            "call_type": "video",
        }
        res = self.app_ctrl.start_whatsapp_video_call("Arun", confirmed=True)
        self.assertEqual(res.get("status"), "CALLING")
        self.mock_whatsapp_ctrl.start_whatsapp_call.assert_called_once_with("Arun", call_type="video")

    def test_end_whatsapp_call(self) -> None:
        """Verify end_whatsapp_call terminates active call without extra confirmation."""
        self.mock_whatsapp_ctrl.end_whatsapp_call.return_value = {
            "status": "ENDED",
            "verified": True,
        }
        res = self.app_ctrl.end_whatsapp_call()
        self.assertEqual(res.get("status"), "ENDED")
        self.mock_whatsapp_ctrl.end_whatsapp_call.assert_called_once()

    def test_get_whatsapp_call_status(self) -> None:
        """Verify get_whatsapp_call_status queries active call state."""
        self.mock_whatsapp_ctrl.get_call_status.return_value = {
            "status": "IDLE",
            "is_active": False,
        }
        res = self.app_ctrl.get_whatsapp_call_status()
        self.assertEqual(res.get("status"), "IDLE")
        self.mock_whatsapp_ctrl.get_call_status.assert_called_once()


if __name__ == "__main__":
    unittest.main()
