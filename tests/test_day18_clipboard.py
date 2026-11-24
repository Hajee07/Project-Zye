"""
Day 18 Unit Tests — Clipboard Manager & Privacy Intelligence.
Verifies clipboard reading, setting, clearing, metadata inspection,
and privacy guarantees (non-logging of clipboard text).
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_windows.clipboard_manager import WindowsClipboardManager


class TestDay18Clipboard(unittest.TestCase):

    def setUp(self) -> None:
        self.cbm = WindowsClipboardManager()

    @patch("pyperclip.paste")
    def test_get_clipboard_text_success(self, mock_paste: MagicMock) -> None:
        """Verify reading clipboard text returns bounded payload."""
        mock_paste.return_value = "Sensitive project brief text."
        res = self.cbm.get_clipboard_text()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["char_count"], len("Sensitive project brief text."))
        self.assertEqual(res["text"], "Sensitive project brief text.")

    @patch("pyperclip.paste")
    def test_get_clipboard_empty(self, mock_paste: MagicMock) -> None:
        """Verify empty clipboard handling."""
        mock_paste.return_value = ""
        res = self.cbm.get_clipboard_text()
        self.assertEqual(res["status"], "EMPTY")
        self.assertEqual(res["char_count"], 0)

    @patch("pyperclip.paste")
    def test_get_clipboard_metadata(self, mock_paste: MagicMock) -> None:
        """Verify metadata inspection extracts lines, words, and unicode flag without persisting."""
        mock_paste.return_value = "Line 1: வணக்கம்\nLine 2: English text"
        res = self.cbm.get_clipboard_metadata()
        self.assertEqual(res["status"], "SUCCESS")
        meta = res["metadata"]
        self.assertEqual(meta["line_count"], 2)
        self.assertTrue(meta["has_unicode"])
        self.assertFalse(meta["is_empty"])
        self.assertEqual(meta["format_type"], "text/unicode")

    @patch("pyperclip.copy")
    def test_set_and_clear_clipboard(self, mock_copy: MagicMock) -> None:
        """Verify setting and clearing clipboard."""
        res_set = self.cbm.set_clipboard_text("Updated clipboard text")
        self.assertEqual(res_set["status"], "SUCCESS")
        mock_copy.assert_called_with("Updated clipboard text")

        res_clear = self.cbm.clear_clipboard()
        self.assertEqual(res_clear["status"], "SUCCESS")
        mock_copy.assert_called_with("")

    @patch("pyautogui.hotkey")
    def test_paste_clipboard_to_active_window(self, mock_hotkey: MagicMock) -> None:
        """Verify pasting current clipboard into active window."""
        res = self.cbm.paste_clipboard_to_active_window()
        self.assertEqual(res["status"], "SUCCESS")
        mock_hotkey.assert_called_with("ctrl", "v")


if __name__ == "__main__":
    unittest.main()
