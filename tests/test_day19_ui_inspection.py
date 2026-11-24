"""
Day 19 Unit Tests — Windows UI Automation Accessibility Tree Inspection.
Verifies element discovery, control type filtering, tree extraction,
and duplicate/stale control handling.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_windows.ui_automation import WindowsUIAutomation


class TestDay19UIInspection(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_inspector = MagicMock()
        self.mock_interaction = MagicMock()
        self.mock_input_ctrl = MagicMock()

        self.uia = WindowsUIAutomation(
            inspector=self.mock_inspector,
            interaction=self.mock_interaction,
            input_ctrl=self.mock_input_ctrl,
            max_elements=40,
        )

        self.sample_controls = [
            {"name": "Search", "control_type": "Edit", "automation_id": "SearchEditBox", "is_enabled": True},
            {"name": "Send", "control_type": "Button", "automation_id": "SendButton", "is_enabled": True},
            {"name": "Voice call", "control_type": "Button", "automation_id": "AudioCallButton", "is_enabled": True},
            {"name": "Video call", "control_type": "Button", "automation_id": "VideoCallButton", "is_enabled": True},
            {"name": "Chat list", "control_type": "List", "automation_id": "ChatList", "is_enabled": True},
        ]
        self.mock_inspector.inspect_app_ui.return_value = {
            "status": "SUCCESS",
            "window": "WhatsApp",
            "controls": self.sample_controls,
        }

    def test_inspect_app_ui_delegation(self) -> None:
        """Verify inspect_app_ui delegates with window keyword and max controls."""
        res = self.uia.inspect_app_ui("WhatsApp", max_controls=25)
        self.assertEqual(res.get("status"), "SUCCESS")
        self.mock_inspector.inspect_app_ui.assert_called_once_with("WhatsApp", max_controls=25)

    def test_find_ui_element_unique(self) -> None:
        """Verify find_ui_element identifies unique control by name."""
        res = self.uia.find_ui_element("WhatsApp", "Send")
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertTrue(res.get("unique"))
        self.assertEqual(res.get("element", {}).get("name"), "Send")

    def test_find_ui_element_by_automation_id(self) -> None:
        """Verify find_ui_element locates element by automation ID."""
        res = self.uia.find_ui_element("WhatsApp", "AudioCallButton")
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertEqual(res.get("element", {}).get("name"), "Voice call")

    def test_find_ui_element_with_type_filter(self) -> None:
        """Verify find_ui_element filters by control type."""
        res = self.uia.find_ui_element("WhatsApp", "Search", control_type="Edit")
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertEqual(res.get("element", {}).get("control_type"), "Edit")

    def test_find_ui_element_not_found(self) -> None:
        """Verify find_ui_element returns NOT_FOUND for unknown element."""
        res = self.uia.find_ui_element("WhatsApp", "CompletelyUnknownButton")
        self.assertEqual(res.get("status"), "NOT_FOUND")

    def test_get_ui_element_details(self) -> None:
        """Verify get_ui_element_details returns complete element dictionary."""
        res = self.uia.get_ui_element_details("WhatsApp", "Voice call")
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertEqual(res.get("details", {}).get("automation_id"), "AudioCallButton")


if __name__ == "__main__":
    unittest.main()
