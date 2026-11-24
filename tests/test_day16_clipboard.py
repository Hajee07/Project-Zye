"""Day 16 Unit Tests — Safe Clipboard Manager & Universal Dictation."""
import unittest
from unittest.mock import MagicMock, patch

from zye_windows.clipboard_manager import WindowsClipboardManager
from zye_windows.input_controller import WindowsInputController


class TestWindowsClipboardManager(unittest.TestCase):
    def setUp(self):
        self.clipboard = WindowsClipboardManager(max_chars=100)
        self.input_ctrl = WindowsInputController()

    @patch("pyperclip.paste")
    def test_get_clipboard_empty(self, mock_paste):
        mock_paste.return_value = ""
        res = self.clipboard.get_clipboard_text()
        self.assertEqual(res["status"], "EMPTY")
        self.assertEqual(res["char_count"], 0)

    @patch("pyperclip.paste")
    def test_get_clipboard_bounded(self, mock_paste):
        long_text = "A" * 500
        mock_paste.return_value = long_text
        res = self.clipboard.get_clipboard_text(max_chars=50)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["returned_count"], 50)
        self.assertEqual(res["char_count"], 500)
        self.assertTrue(res["truncated"])

    @patch("pyperclip.copy")
    def test_set_clipboard_text(self, mock_copy):
        res = self.clipboard.set_clipboard_text("Hello World")
        self.assertEqual(res["status"], "SUCCESS")
        mock_copy.assert_called_with("Hello World")

    @patch("pyperclip.copy")
    def test_clear_clipboard(self, mock_copy):
        res = self.clipboard.clear_clipboard()
        self.assertEqual(res["status"], "SUCCESS")
        mock_copy.assert_called_with("")

    @patch("pyperclip.paste")
    @patch("pyperclip.copy")
    @patch("pyautogui.hotkey")
    def test_dictate_text_preserves_previous_clipboard(self, mock_hotkey, mock_copy, mock_paste):
        mock_paste.return_value = "Previous Secret"
        tamil_text = "வணக்கம் Zye, எப்படி இருக்கீங்க?"

        res = self.input_ctrl.dictate_text_anywhere(tamil_text, press_enter=False)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["verified"])
        # Should copy new text, paste, then restore old text
        mock_hotkey.assert_called_with("ctrl", "v")
        # Ensure previous clipboard was restored
        self.assertEqual(mock_copy.call_args_list[-1][0][0], "Previous Secret")

    def test_press_hotkey_unauthorized_key_rejected(self):
        res = self.input_ctrl.press_hotkey(["ctrl", "evil_key_123"])
        self.assertEqual(res["status"], "REJECTED")

    @patch("pyautogui.hotkey")
    def test_press_hotkey_authorized(self, mock_hotkey):
        res = self.input_ctrl.press_hotkey(["ctrl", "c"])
        self.assertEqual(res["status"], "SUCCESS")
        mock_hotkey.assert_called_with("ctrl", "c")


if __name__ == "__main__":
    unittest.main()
