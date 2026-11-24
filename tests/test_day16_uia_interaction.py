"""Day 16 Unit Tests — Named UI Element Interaction Engine."""
import unittest
from unittest.mock import MagicMock, patch

from zye_windows.uia_interaction import WindowsUIAInteraction


class TestWindowsUIAInteraction(unittest.TestCase):
    def setUp(self):
        self.interaction = WindowsUIAInteraction()

    def test_empty_arguments(self):
        res = self.interaction.click_ui_element("", "Send")
        self.assertEqual(res["status"], "ERROR")
        res2 = self.interaction.click_ui_element("WhatsApp", "")
        self.assertEqual(res2["status"], "ERROR")

    @patch("zye_windows.uia_interaction.Desktop")
    def test_window_not_found(self, mock_desktop_cls):
        mock_desktop = MagicMock()
        mock_desktop.windows.return_value = []
        mock_desktop_cls.return_value = mock_desktop

        res = self.interaction.click_ui_element("NonExistentWindow", "Button")
        self.assertEqual(res["status"], "WINDOW_NOT_FOUND")

    @patch("zye_windows.uia_interaction.Desktop")
    def test_element_not_found(self, mock_desktop_cls):
        mock_desktop = MagicMock()
        mock_target = MagicMock()
        mock_target.window_text.return_value = "Notepad"
        mock_target.descendants.return_value = []
        mock_desktop.windows.return_value = [mock_target]
        mock_desktop_cls.return_value = mock_desktop

        res = self.interaction.click_ui_element("Notepad", "SaveAsButton")
        self.assertEqual(res["status"], "ELEMENT_NOT_FOUND")

    @patch("zye_windows.uia_interaction.Desktop")
    def test_ambiguous_elements(self, mock_desktop_cls):
        mock_desktop = MagicMock()
        mock_target = MagicMock()
        mock_target.window_text.return_value = "WhatsApp"

        e1 = MagicMock()
        e1.element_info.name = "Call Option 1"
        e1.element_info.automation_id = "opt1"
        e1.element_info.control_type = "Button"

        e2 = MagicMock()
        e2.element_info.name = "Call Option 2"
        e2.element_info.automation_id = "opt2"
        e2.element_info.control_type = "Button"

        mock_target.descendants.return_value = [e1, e2]
        mock_desktop.windows.return_value = [mock_target]
        mock_desktop_cls.return_value = mock_desktop

        res = self.interaction.click_ui_element("WhatsApp", "Call")
        self.assertEqual(res["status"], "AMBIGUOUS_ELEMENT")
        self.assertEqual(len(res["candidates"]), 2)

    @patch("zye_windows.uia_interaction.Desktop")
    def test_disabled_element(self, mock_desktop_cls):
        mock_desktop = MagicMock()
        mock_target = MagicMock()
        mock_target.window_text.return_value = "Form"

        btn = MagicMock()
        btn.element_info.name = "Submit"
        btn.element_info.automation_id = "submit_btn"
        btn.element_info.control_type = "Button"
        btn.element_info.enabled = False

        mock_target.descendants.return_value = [btn]
        mock_desktop.windows.return_value = [mock_target]
        mock_desktop_cls.return_value = mock_desktop

        res = self.interaction.click_ui_element("Form", "Submit")
        self.assertEqual(res["status"], "ELEMENT_DISABLED")

    @patch("zye_windows.uia_interaction.Desktop")
    def test_successful_click_fallback(self, mock_desktop_cls):
        mock_desktop = MagicMock()
        mock_target = MagicMock()
        mock_target.window_text.return_value = "Editor"

        btn = MagicMock(spec=["element_info", "click_input"])
        btn.element_info = MagicMock()
        btn.element_info.name = "Save"
        btn.element_info.automation_id = "save_btn"
        btn.element_info.control_type = "Button"
        btn.element_info.enabled = True

        mock_target.descendants.return_value = [btn]
        mock_desktop.windows.return_value = [mock_target]
        mock_desktop_cls.return_value = mock_desktop

        res = self.interaction.click_ui_element("Editor", "Save")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["invocation_method"], "click_input")
        btn.click_input.assert_called_once()


if __name__ == "__main__":
    unittest.main()
