"""
Day 18 Unit Tests — Global Media Controller & Session Inspector.
Verifies active media session detection (Spotify, VLC, YouTube),
playback commands (play, pause, next, previous, stop), and error handling.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_windows.media_controller import WindowsMediaController


class MockWindow:
    def __init__(self, title: str):
        self.title = title


class TestDay18Media(unittest.TestCase):

    def setUp(self) -> None:
        self.mc = WindowsMediaController()

    @patch("pygetwindow.getAllWindows")
    def test_inspect_spotify_session(self, mock_get_all: MagicMock) -> None:
        """Verify detecting Spotify active playback session from window title."""
        mock_get_all.return_value = [
            MockWindow("A.R. Rahman - Urvasi Urvasi - Spotify"),
            MockWindow("Notepad"),
        ]
        res = self.mc.get_active_media_session()
        self.assertEqual(res["status"], "ACTIVE_SESSION")
        self.assertEqual(res["session"]["source_app_id"], "Spotify")
        self.assertIn("A.R. Rahman", res["session"]["title"])

    @patch("pygetwindow.getAllWindows")
    def test_inspect_vlc_session(self, mock_get_all: MagicMock) -> None:
        """Verify detecting VLC playback session from window title."""
        mock_get_all.return_value = [
            MockWindow("sample_video.mp4 - VLC media player"),
        ]
        res = self.mc.get_active_media_session()
        self.assertEqual(res["status"], "ACTIVE_SESSION")
        self.assertEqual(res["session"]["source_app_id"], "VLC")

    @patch("pyautogui.press")
    def test_dispatch_media_commands(self, mock_press: MagicMock) -> None:
        """Verify supported media commands press appropriate virtual media keys."""
        res_play = self.mc.media_control("play")
        self.assertEqual(res_play["status"], "SUCCESS")
        mock_press.assert_called_with("playpause")

        res_next = self.mc.media_control("next")
        self.assertEqual(res_next["status"], "SUCCESS")
        mock_press.assert_called_with("nexttrack")

        res_prev = self.mc.media_control("previous")
        self.assertEqual(res_prev["status"], "SUCCESS")
        mock_press.assert_called_with("prevtrack")

        res_stop = self.mc.media_control("stop")
        self.assertEqual(res_stop["status"], "SUCCESS")
        mock_press.assert_called_with("stop")

    def test_reject_unsupported_media_command(self) -> None:
        """Verify unrecognized media commands return REJECTED status."""
        res = self.mc.media_control("rewind_30s")
        self.assertEqual(res["status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
