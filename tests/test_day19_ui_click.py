"""
Day 19 Unit Tests — Safe UI Element Click Engine.
Verifies clicking valid buttons, rejecting disabled/ambiguous controls,
pattern invocation, and click verification.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from zye_windows.ui_automation import WindowsUIAutomation


class TestDay19UIClick(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_inspector = MagicMock()
        self.mock_interaction = MagicMock()
        self.mock_input_ctrl = MagicMock()

        self.uia = WindowsUIAutomation(
            inspector=self.mock_inspector,
            interaction=self.mock_interaction,
            input_ctrl=self.mock_input_ctrl,
        )

        self.sample_controls = [
            {"name": "Save", "control_type": "Button", "automation_id": "btnSave", "is_enabled": True},
            {"name": "Cancel", "control_type": "Button", "automation_id": "btnCancel", "is_enabled": False},
            {"name": "Submit", "control_type": "Button", "automation_id": "btnSubmit1", "is_enabled": True},
            {"name": "Submit", "control_type": "Button", "automation_id": "btnSubmit2", "is_enabled": True},
        ]
        self.mock_inspector.inspect_app_ui.return_value = {
            "status": "SUCCESS",
            "window": "TestApp",
            "controls": self.sample_controls,
        }

    def test_click_valid_button(self) -> None:
        """Verify click_ui_element executes for enabled unique button."""
        self.mock_interaction.click_ui_element.return_value = {
            "status": "SUCCESS",
            "window": "TestApp",
            "element": "Save",
            "verified": True,
        }
        res = self.uia.click_ui_element("TestApp", "Save")
        self.assertEqual(res.get("status"), "SUCCESS")
        self.mock_interaction.click_ui_element.assert_called_once_with(
            window_keyword="TestApp",
            element_name="Save",
            control_type="",
        )

    def test_click_disabled_button_rejected(self) -> None:
        """Verify click_ui_element rejects disabled button without clicking."""
        res = self.uia.click_ui_element("TestApp", "Cancel")
        self.assertEqual(res.get("status"), "ELEMENT_DISABLED")
        self.mock_interaction.click_ui_element.assert_not_called()

    def test_click_ambiguous_button_rejected(self) -> None:
        """Verify click_ui_element detects multiple matching controls and requires disambiguation."""
        res = self.uia.click_ui_element("TestApp", "Submit")
        self.assertEqual(res.get("status"), "AMBIGUOUS_ELEMENT")
        self.assertFalse(res.get("unique"))
        self.mock_interaction.click_ui_element.assert_not_called()

    def test_click_non_existent_element(self) -> None:
        """Verify click_ui_element returns NOT_FOUND for unknown element."""
        res = self.uia.click_ui_element("TestApp", "NonExistent")
        self.assertEqual(res.get("status"), "NOT_FOUND")
        self.mock_interaction.click_ui_element.assert_not_called()


if __name__ == "__main__":
    unittest.main()
