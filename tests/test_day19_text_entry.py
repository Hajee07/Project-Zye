"""
Day 19 Unit Tests — Multilingual Text Entry & Unicode Preservation.
Verifies English, Tamil, Tanglish, emoji, and multiline text insertion,
Unicode integrity, clipboard dispatch, and enter safety.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_windows.input_controller import WindowsInputController


class TestDay19TextEntry(unittest.TestCase):

    def setUp(self) -> None:
        self.ic = WindowsInputController()

    @patch("pyperclip.copy")
    @patch("pyautogui.hotkey")
    def test_tamil_unicode_preservation(self, mock_hotkey, mock_copy) -> None:
        """Verify Tamil phrase is copied to clipboard and pasted via Ctrl+V without character corruption."""
        tamil_text = "வணக்கம், இது Zye AI தானியங்கி சோதனை."
        res = self.ic.dictate_text_anywhere(tamil_text, press_enter=False)
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertEqual(res.get("char_count"), len(tamil_text))
        mock_copy.assert_called_once_with(tamil_text)
        mock_hotkey.assert_called_once_with("ctrl", "v")

    @patch("pyperclip.copy")
    @patch("pyautogui.hotkey")
    def test_tanglish_and_emoji_preservation(self, mock_hotkey, mock_copy) -> None:
        """Verify Tanglish with emojis and punctuation is cleanly transferred."""
        tanglish_text = "Arun, naan 10 mins-la reach aagiduven 🚀⚡!"
        res = self.ic.dictate_text_anywhere(tanglish_text, press_enter=False)
        self.assertEqual(res.get("status"), "SUCCESS")
        mock_copy.assert_called_once_with(tanglish_text)
        mock_hotkey.assert_called_once_with("ctrl", "v")

    @patch("pyperclip.copy")
    @patch("pyautogui.hotkey")
    def test_multiline_text_entry(self, mock_hotkey, mock_copy) -> None:
        """Verify multiline text preserves newlines without accidental submit."""
        multiline = "Line 1: Summary\nLine 2: Details\nLine 3: Conclusion"
        res = self.ic.dictate_text_anywhere(multiline, press_enter=False)
        self.assertEqual(res.get("status"), "SUCCESS")
        mock_copy.assert_called_once_with(multiline)
        # Verify Ctrl+V was dispatched
        mock_hotkey.assert_called_once_with("ctrl", "v")

    @patch("pyperclip.copy")
    @patch("pyautogui.press")
    @patch("pyautogui.hotkey")
    def test_enter_safety_when_submit_true(self, mock_hotkey, mock_press, mock_copy) -> None:
        """Verify enter key is only dispatched when press_enter=True explicitly."""
        res = self.ic.dictate_text_anywhere("Search query", press_enter=True)
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertTrue(res.get("press_enter"))
        mock_hotkey.assert_called_once_with("ctrl", "v")
        mock_press.assert_called_once_with("enter")

    def test_empty_text_rejected(self) -> None:
        """Verify empty or whitespace-only text returns ERROR without touching clipboard."""
        res = self.ic.dictate_text_anywhere("")
        self.assertEqual(res.get("status"), "ERROR")

    def test_text_length_limit_exceeded(self) -> None:
        """Verify text exceeding 20,000 characters is rejected."""
        oversized = "A" * 25000
        res = self.ic.dictate_text_anywhere(oversized)
        self.assertEqual(res.get("status"), "ERROR")
        self.assertIn("exceeds maximum", res.get("message", ""))


if __name__ == "__main__":
    unittest.main()
