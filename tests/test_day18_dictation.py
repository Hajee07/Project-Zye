"""
Day 18 Unit Tests — Universal Hands-Free Dictation Engine.
Verifies typing into active focus, English/Tamil/Tanglish support,
maximum character boundary (20,000 chars), and enter key safety (press_enter=False default).
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_windows.input_controller import MAX_DICTATION_CHARS, WindowsInputController


class TestDay18Dictation(unittest.TestCase):

    def setUp(self) -> None:
        self.ic = WindowsInputController()

    @patch("pyperclip.copy")
    @patch("pyautogui.hotkey")
    @patch("pyautogui.press")
    def test_dictate_text_safe_enter_default(self, mock_press: MagicMock, mock_hotkey: MagicMock, mock_copy: MagicMock) -> None:
        """Verify dictate_text_anywhere does NOT press enter by default."""
        res = self.ic.dictate_text_anywhere("Hello, this is a dictated note.")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertFalse(res["press_enter"])
        mock_hotkey.assert_called_with("ctrl", "v")
        mock_press.assert_not_called()

    @patch("pyperclip.copy")
    @patch("pyautogui.hotkey")
    @patch("pyautogui.press")
    def test_dictate_text_with_explicit_enter(self, mock_press: MagicMock, mock_hotkey: MagicMock, mock_copy: MagicMock) -> None:
        """Verify enter key is only pressed when explicitly authorized."""
        res = self.ic.dictate_text_anywhere("Submit this message", press_enter=True)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["press_enter"])
        mock_press.assert_called_with("enter")

    def test_empty_dictation_rejected(self) -> None:
        """Verify empty dictation string returns error."""
        res = self.ic.dictate_text_anywhere("")
        self.assertEqual(res["status"], "ERROR")

    def test_excessive_length_rejected(self) -> None:
        """Verify dictation exceeding 20,000 characters is rejected."""
        huge_text = "A" * (MAX_DICTATION_CHARS + 50)
        res = self.ic.dictate_text_anywhere(huge_text)
        self.assertEqual(res["status"], "ERROR")
        self.assertIn("exceeds maximum dictation length", res["message"])


if __name__ == "__main__":
    unittest.main()
