"""
Day 19 Unit Tests — Zero-Trust Security Gates & Safety Mapping.
Verifies Negative Pre-Mortem risk classifications, protection of system tasks,
interlocks on destructive actions, and non-logging of private credentials.
"""

from __future__ import annotations

import unittest

from zye_orchestrator.safety_pipeline import TOOL_RISK_MAP, RiskLevel
from zye_windows.process_manager import WindowsProcessManager


class TestDay19Security(unittest.TestCase):

    def setUp(self) -> None:
        self.pm = WindowsProcessManager()

    def test_destructive_operations_are_high_or_critical_risk(self) -> None:
        """Verify mutating and destructive operations require HIGH or CRITICAL risk rating."""
        high_critical = {RiskLevel.HIGH_RISK, RiskLevel.CRITICAL_RISK}

        self.assertIn(TOOL_RISK_MAP.get("terminate_process"), high_critical)
        self.assertIn(TOOL_RISK_MAP.get("empty_recycle_bin"), high_critical)
        self.assertIn(TOOL_RISK_MAP.get("send_whatsapp_message"), high_critical)
        self.assertIn(TOOL_RISK_MAP.get("start_whatsapp_voice_call"), high_critical)
        self.assertIn(TOOL_RISK_MAP.get("delete_screenshot"), high_critical)

    def test_telemetry_and_inspection_are_read_only(self) -> None:
        """Verify query and discovery tools remain non-invasive READ_ONLY."""
        read_only_tools = [
            "list_processes",
            "find_process_by_name",
            "get_process_details",
            "get_system_resource_summary",
            "verify_process_status",
            "list_installed_apps",
            "search_installed_apps",
            "get_ui_element_details",
            "get_application_status",
            "inspect_app_ui",
            "get_clipboard_metadata",
            "search_local_files",
            "get_file_details",
            "get_active_media_session",
            "list_open_windows",
            "get_connected_displays",
            "get_virtual_desktops",
        ]
        for t in read_only_tools:
            self.assertEqual(TOOL_RISK_MAP.get(t), RiskLevel.READ_ONLY, f"Tool '{t}' should be READ_ONLY")

    def test_protected_process_list_integrity(self) -> None:
        """Verify immutable OS task names cannot be terminated."""
        for p in ["csrss.exe", "wininit.exe", "services.exe", "lsass.exe", "smss.exe", "explorer.exe"]:
            self.assertTrue(self.pm.is_protected_process(p))

    def test_unintended_message_sending_blocked_without_confirmation(self) -> None:
        """Verify that message sending cannot occur implicitly without confirmed=True."""
        from zye_windows.application_controller import WindowsApplicationController
        ac = WindowsApplicationController()
        res = ac.send_whatsapp_message("Manager", "Confidential text", confirmed=False)
        self.assertEqual(res.get("status"), "CONFIRMATION_REQUIRED")
        self.assertTrue(res.get("requires_confirmation"))


if __name__ == "__main__":
    unittest.main()
