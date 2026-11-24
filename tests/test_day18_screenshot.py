"""
Day 18 Unit Tests — Desktop & Active Window Screenshot Manager.
Verifies full desktop capture, active window crop capture, screenshot cataloguing,
retention management, and deletion confirmation gates.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from zye_windows.screenshot_manager import WindowsScreenshotManager


class MockActiveWindow:
    def __init__(self, title: str = "Active Window"):
        self.title = title
        self.left = 100
        self.top = 100
        self.width = 640
        self.height = 480


class MockImage:
    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height

    def save(self, target_path: str):
        Path(target_path).write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRdummy_bytes")


class TestDay18Screenshot(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)
        self.sm = WindowsScreenshotManager(output_dir=self.output_dir)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @patch("pyautogui.screenshot")
    def test_capture_full_screenshot(self, mock_shot: MagicMock) -> None:
        """Verify full desktop screenshot is written to disk and returns file metadata."""
        mock_shot.return_value = MockImage(1920, 1080)

        res = self.sm.capture_screenshot()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(Path(res["file_path"]).exists())
        self.assertEqual(res["width"], 1920)
        self.assertEqual(res["height"], 1080)

    @patch("pygetwindow.getActiveWindow")
    @patch("pyautogui.screenshot")
    def test_capture_active_window(self, mock_shot: MagicMock, mock_active: MagicMock) -> None:
        """Verify active window screenshot uses crop coordinates from active window."""
        mock_active.return_value = MockActiveWindow("VS Code")
        mock_shot.return_value = MockImage(640, 480)

        res = self.sm.capture_active_window()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["window_title"], "VS Code")
        mock_shot.assert_called_with(region=(100, 100, 640, 480))

    def test_list_and_delete_screenshot(self) -> None:
        """Verify listing screenshots and deleting with explicit confirmation."""
        sample = self.output_dir / "screenshot_test.png"
        sample.write_text("dummy", encoding="utf-8")

        shots = self.sm.list_screenshots()
        self.assertEqual(len(shots), 1)
        self.assertEqual(shots[0]["filename"], "screenshot_test.png")

        # Unconfirmed deletion should require confirmation
        unconf = self.sm.delete_screenshot(str(sample), confirmed=False)
        self.assertEqual(unconf["status"], "CONFIRMATION_REQUIRED")
        self.assertTrue(sample.exists())

        # Confirmed deletion succeeds
        conf = self.sm.delete_screenshot(str(sample), confirmed=True)
        self.assertEqual(conf["status"], "DELETED")
        self.assertFalse(sample.exists())


if __name__ == "__main__":
    unittest.main()
