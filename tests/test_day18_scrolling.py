"""
Day 18 Unit Tests — Intelligent Wheel Scrolling Engine.
Verifies scroll direction validation, magnitude clamping (1..50 steps),
and PyAutoGUI wheel step conversion.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_windows.input_controller import WindowsInputController


class TestDay18Scrolling(unittest.TestCase):

    def setUp(self) -> None:
        self.ic = WindowsInputController()

    @patch("pyautogui.scroll")
    def test_scroll_down_and_up(self, mock_scroll: MagicMock) -> None:
        """Verify vertical scrolling dispatches positive (up) and negative (down) clicks."""
        res_down = self.ic.scroll_page(direction="down", amount=5)
        self.assertEqual(res_down["status"], "SUCCESS")
        self.assertEqual(res_down["direction"], "down")
        self.assertEqual(res_down["steps"], 5)
        mock_scroll.assert_called_with(-500)

        res_up = self.ic.scroll_page(direction="up", amount=3)
        self.assertEqual(res_up["status"], "SUCCESS")
        self.assertEqual(res_up["direction"], "up")
        self.assertEqual(res_up["steps"], 3)
        mock_scroll.assert_called_with(300)

    @patch("pyautogui.scroll")
    def test_scroll_bounds_clamped(self, mock_scroll: MagicMock) -> None:
        """Verify scroll amount is strictly clamped between 1 and 50."""
        # Excessively large amount 500 should be clamped to 50
        res_large = self.ic.scroll_page(direction="down", amount=500)
        self.assertEqual(res_large["status"], "SUCCESS")
        self.assertEqual(res_large["steps"], 50)
        mock_scroll.assert_called_with(-5000)

        # Negative/zero amount clamped to 1
        res_neg = self.ic.scroll_page(direction="up", amount=-10)
        self.assertEqual(res_neg["status"], "SUCCESS")
        self.assertEqual(res_neg["steps"], 1)
        mock_scroll.assert_called_with(100)

    def test_invalid_direction_rejected(self) -> None:
        """Verify invalid scroll direction returns error response."""
        res = self.ic.scroll_page(direction="diagonal", amount=5)
        self.assertEqual(res["status"], "ERROR")
        self.assertIn("Invalid scroll direction", res["message"])


if __name__ == "__main__":
    unittest.main()
