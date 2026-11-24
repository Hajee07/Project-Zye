"""Day 16 Unit Tests — Windows UI Automation Accessibility Tree Inspector."""
import unittest
from unittest.mock import MagicMock, patch

from zye_windows.uia_inspector import WindowsUIAInspector


class TestWindowsUIAInspector(unittest.TestCase):
    def setUp(self):
        self.inspector = WindowsUIAInspector(max_controls=60)

    def test_empty_keyword_rejected(self):
        res = self.inspector.inspect_app_ui("")
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res["controls"], [])

    @patch("zye_windows.uia_inspector.Desktop")
    def test_window_not_found(self, mock_desktop_cls):
        mock_desktop = MagicMock()
        mock_win1 = MagicMock()
        mock_win1.window_text.return_value = "Command Prompt"
        mock_desktop.windows.return_value = [mock_win1]
        mock_desktop_cls.return_value = mock_desktop

        res = self.inspector.inspect_app_ui("Calculator")
        self.assertEqual(res["status"], "WINDOW_NOT_FOUND")
        self.assertEqual(res["controls"], [])
        self.assertIn("Command Prompt", res["available_windows"])

    @patch("zye_windows.uia_inspector.Desktop")
    def test_window_inspect_controls_and_bounding(self, mock_desktop_cls):
        mock_desktop = MagicMock()
        mock_target = MagicMock()
        mock_target.window_text.return_value = "WhatsApp"
        mock_target.handle = 12345
        mock_desktop.windows.return_value = [mock_target]
        mock_desktop_cls.return_value = mock_desktop

        # Create mock controls
        mock_ctrls = []
        for i in range(100):
            c = MagicMock()
            c.window_text.return_value = f"Button_{i}"
            c.element_info.control_type = "Button"
            c.element_info.automation_id = f"auto_id_{i}"
            c.is_enabled.return_value = True
            c.is_visible.return_value = True
            c.rectangle.return_value = MagicMock(left=10, top=10, right=100, bottom=50)
            mock_ctrls.append(c)

        mock_target.descendants.return_value = mock_ctrls

        res = self.inspector.inspect_app_ui("WhatsApp", max_controls=20)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(len(res["controls"]), 20)
        self.assertEqual(res["controls_count"], 20)
        self.assertTrue(res["truncated"])

    @patch("zye_windows.uia_inspector.Desktop")
    def test_sensitive_password_redaction(self, mock_desktop_cls):
        mock_desktop = MagicMock()
        mock_target = MagicMock()
        mock_target.window_text.return_value = "Login"
        mock_target.handle = 54321
        mock_desktop.windows.return_value = [mock_target]
        mock_desktop_cls.return_value = mock_desktop

        pwd_ctrl = MagicMock()
        pwd_ctrl.window_text.return_value = "SuperSecretPassword123"
        pwd_ctrl.element_info.control_type = "Edit"
        pwd_ctrl.element_info.automation_id = "password_input"
        pwd_ctrl.is_enabled.return_value = True
        pwd_ctrl.is_visible.return_value = True
        pwd_ctrl.rectangle.return_value = MagicMock(left=0, top=0, right=50, bottom=20)

        mock_target.descendants.return_value = [pwd_ctrl]

        res = self.inspector.inspect_app_ui("Login")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(len(res["controls"]), 1)
        # Check that password text is redacted
        ctrl_name = res["controls"][0]["name"]
        self.assertNotEqual(ctrl_name, "SuperSecretPassword123")


if __name__ == "__main__":
    unittest.main()
