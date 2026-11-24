"""
Day 18 Unit Tests — Unicode Preservation & Multilingual Integrity.
Verifies Tamil Unicode characters (\u0b80-\u0bff), emojis, mathematical symbols,
and multiline string integrity through clipboard copy/paste.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_windows.input_controller import WindowsInputController


class TestDay18Unicode(unittest.TestCase):

    def setUp(self) -> None:
        self.ic = WindowsInputController()

    @patch("pyperclip.copy")
    @patch("pyautogui.hotkey")
    def test_tamil_unicode_dictation(self, mock_hotkey: MagicMock, mock_copy: MagicMock) -> None:
        """Verify Tamil sentences are copied to clipboard byte-for-byte without corruption."""
        tamil_text = "வணக்கம்! நான் Zye AI, உங்கள் தனிப்பட்ட உதவியாளர்."
        res = self.ic.dictate_text_anywhere(tamil_text)
        self.assertEqual(res["status"], "SUCCESS")
        # Ensure pyperclip.copy was invoked with the exact Tamil string
        mock_copy.assert_any_call(tamil_text)

    @patch("pyperclip.copy")
    @patch("pyautogui.hotkey")
    def test_emoji_and_symbols_preservation(self, mock_hotkey: MagicMock, mock_copy: MagicMock) -> None:
        """Verify emojis and special mathematical symbols are preserved."""
        emoji_text = "Meeting at 3 PM 🕒 📅 | Revenue: ₹50,000 | α + β = γ ✨"
        res = self.ic.dictate_text_anywhere(emoji_text)
        self.assertEqual(res["status"], "SUCCESS")
        mock_copy.assert_any_call(emoji_text)

    @patch("pyperclip.copy")
    @patch("pyautogui.hotkey")
    def test_multiline_formatting_preservation(self, mock_hotkey: MagicMock, mock_copy: MagicMock) -> None:
        """Verify newlines and indentation are preserved."""
        multiline_code = (
            "def calculate_total(items):\n"
            "    # தமிழ் குறிப்பு\n"
            "    return sum(items)\n"
        )
        res = self.ic.dictate_text_anywhere(multiline_code)
        self.assertEqual(res["status"], "SUCCESS")
        mock_copy.assert_any_call(multiline_code)


if __name__ == "__main__":
    unittest.main()
