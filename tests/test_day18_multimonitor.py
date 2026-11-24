"""
Day 18 Unit Tests — Multi-Monitor Awareness & Window Movement.
Verifies display enumeration, primary screen identification, window monitor detection,
and cross-monitor window repositioning.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_windows.display_manager import WindowsDisplayManager
from zye_windows.windows_models import DisplayInfo


class MockWindow:
    def __init__(self, title: str, hwnd: int = 701, left: int = 100, top: int = 100, width: int = 800, height: int = 600):
        self.title = title
        self._hWnd = hwnd
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.isMaximized = False

    def restore(self):
        self.isMaximized = False

    def maximize(self):
        self.isMaximized = True

    def moveTo(self, x: int, y: int):
        self.left = x
        self.top = y


class TestDay18MultiMonitor(unittest.TestCase):

    def setUp(self) -> None:
        self.dm = WindowsDisplayManager()

    def test_get_connected_displays_returns_at_least_one(self) -> None:
        """Verify connected displays returns at least the primary desktop display."""
        displays = self.dm.get_connected_displays()
        self.assertTrue(len(displays) >= 1)
        self.assertTrue(any(d.is_primary for d in displays))
        for d in displays:
            self.assertTrue(d.width > 0)
            self.assertTrue(d.height > 0)

    def test_get_primary_display(self) -> None:
        """Verify get_primary_display returns the primary display object."""
        primary = self.dm.get_primary_display()
        self.assertIsNotNone(primary)
        self.assertTrue(primary.is_primary)

    def test_get_display_details_valid_and_invalid(self) -> None:
        """Verify display detail query for valid and invalid display IDs."""
        res_valid = self.dm.get_display_details(1)
        self.assertEqual(res_valid["status"], "SUCCESS")
        self.assertEqual(res_valid["display"]["display_id"], 1)

        res_invalid = self.dm.get_display_details(999)
        self.assertEqual(res_invalid["status"], "NOT_FOUND")

    @patch("pygetwindow.getAllWindows")
    def test_get_window_monitor(self, mock_get_all: MagicMock) -> None:
        """Verify identifying which monitor contains a given window."""
        win = MockWindow("Chrome", hwnd=801, left=100, top=100)
        mock_get_all.return_value = [win]

        res = self.dm.get_window_monitor("Chrome")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("monitor_id", res)

    @patch("pygetwindow.getAllWindows")
    def test_move_window_to_monitor(self, mock_get_all: MagicMock) -> None:
        """Verify moving a window to target monitor coordinates."""
        win = MockWindow("VS Code", hwnd=901, left=50, top=50)
        mock_get_all.return_value = [win]

        res = self.dm.move_window_to_monitor("VS Code", display_id=1)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["target_display_id"], 1)

        # Invalid monitor ID
        res_bad = self.dm.move_window_to_monitor("VS Code", display_id=999)
        self.assertEqual(res_bad["status"], "DISPLAY_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
