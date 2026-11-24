"""Day 16 Unit Tests — Safety Gateway Risk Mapping & Confirmation Interlocks."""
import unittest

from main import NON_IDEMPOTENT_OPERATIONS, is_safe_to_replay
from zye_orchestrator.safety_pipeline import RiskLevel, SafetyExecutionGateway
from zye_windows.power_manager import WindowsPowerManager
from zye_windows.process_manager import WindowsProcessManager
from zye_windows.whatsapp_controller import WhatsAppController


class TestDay16Security(unittest.TestCase):
    def setUp(self):
        self.gateway = SafetyExecutionGateway()

    def test_day16_risk_levels(self):
        # Critical
        self.assertEqual(self.gateway.classify_risk("power_action"), RiskLevel.CRITICAL_RISK)
        self.assertEqual(self.gateway.classify_risk("empty_recycle_bin"), RiskLevel.CRITICAL_RISK)

        # High
        self.assertEqual(self.gateway.classify_risk("send_whatsapp_message"), RiskLevel.HIGH_RISK)
        self.assertEqual(self.gateway.classify_risk("start_whatsapp_voice_call"), RiskLevel.HIGH_RISK)
        self.assertEqual(self.gateway.classify_risk("start_whatsapp_video_call"), RiskLevel.HIGH_RISK)

        # Medium
        self.assertEqual(self.gateway.classify_risk("control_volume"), RiskLevel.MEDIUM_RISK)
        self.assertEqual(self.gateway.classify_risk("set_brightness"), RiskLevel.MEDIUM_RISK)
        self.assertEqual(self.gateway.classify_risk("snap_window"), RiskLevel.MEDIUM_RISK)
        self.assertEqual(self.gateway.classify_risk("scroll_page"), RiskLevel.MEDIUM_RISK)
        self.assertEqual(self.gateway.classify_risk("press_hotkey"), RiskLevel.MEDIUM_RISK)
        self.assertEqual(self.gateway.classify_risk("manage_window"), RiskLevel.MEDIUM_RISK)

        # Low
        self.assertEqual(self.gateway.classify_risk("open_any_app"), RiskLevel.LOW_RISK)

        # Read Only
        self.assertEqual(self.gateway.classify_risk("inspect_app_ui"), RiskLevel.READ_ONLY)
        self.assertEqual(self.gateway.classify_risk("get_battery_status"), RiskLevel.READ_ONLY)
        self.assertEqual(self.gateway.classify_risk("get_clipboard_text"), RiskLevel.READ_ONLY)

    def test_non_idempotent_operations_membership(self):
        expected_ops = [
            "send_whatsapp_message",
            "start_whatsapp_voice_call",
            "start_whatsapp_video_call",
            "end_whatsapp_call",
            "empty_recycle_bin",
            "power_action",
        ]
        for op in expected_ops:
            self.assertIn(op, NON_IDEMPOTENT_OPERATIONS)
            self.assertFalse(is_safe_to_replay(op))

    def test_unconfirmed_power_action_blocked(self):
        pm = WindowsPowerManager()
        res_sd = pm.power_action("shutdown", confirmed=False)
        self.assertEqual(res_sd["status"], "CONFIRMATION_REQUIRED")
        self.assertTrue(res_sd["requires_user_confirmation"])

        res_rs = pm.power_action("restart", confirmed=False)
        self.assertEqual(res_rs["status"], "CONFIRMATION_REQUIRED")
        self.assertTrue(res_rs["requires_user_confirmation"])

    def test_unconfirmed_whatsapp_message_blocked(self):
        wc = WhatsAppController()
        res = wc.send_whatsapp_message("Mom", "Hi", confirmed=False)
        self.assertEqual(res["status"], "CONFIRMATION_REQUIRED")
        self.assertTrue(res["requires_user_confirmation"])

    def test_unconfirmed_empty_recycle_bin_blocked(self):
        proc_mgr = WindowsProcessManager()
        res = proc_mgr.empty_recycle_bin(confirmed=False)
        self.assertEqual(res["status"], "CONFIRMATION_REQUIRED")
        self.assertTrue(res["requires_user_confirmation"])


if __name__ == "__main__":
    unittest.main()
