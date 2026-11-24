#!/usr/bin/env python3
"""
ZYE AI — Day 10 Pygame Playback Test Suite
==========================================
Tests for zye_voice.playback: ZyeAudioPlayback, PlaybackConfig.
All hardware mixer calls are mocked — CI-safe.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zye_voice.playback import (
    PlaybackConfig,
    PlaybackDeviceUnavailableError,
    PlaybackError,
    ZyeAudioPlayback,
)


class TestZyeAudioPlayback(unittest.TestCase):
    """Test suite for Pygame audio playback engine."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        self.tmp.write(b"fake_mp3_audio_data")
        self.tmp.close()
        self.mp3_path = self.tmp.name

    def tearDown(self):
        p = Path(self.mp3_path)
        if p.is_file():
            try:
                p.unlink()
            except Exception:
                pass

    def _run(self, coro):
        return asyncio.run(coro)

    def test_01_init_with_defaults(self):
        pb = ZyeAudioPlayback()
        self.assertTrue(pb.config.enabled)
        self.assertEqual(pb.config.mixer_frequency, 44100)
        self.assertEqual(pb.config.mixer_channels, 2)
        self.assertFalse(pb._is_playing)

    def test_02_mixer_already_initialized(self):
        with patch("zye_voice.playback.pygame") as mock_pg:
            mock_pg.mixer.get_init.return_value = True
            pb = ZyeAudioPlayback()
            res = pb.initialize()
            self.assertTrue(res)
            # init() shouldn't be called if get_init() is already True
            mock_pg.mixer.init.assert_not_called()

    def test_03_mixer_unavailable_when_disabled(self):
        pb = ZyeAudioPlayback(PlaybackConfig(enabled=False))
        self.assertFalse(pb.initialize())

    def test_04_mixer_unavailable_when_pygame_missing(self):
        with patch("zye_voice.playback._PYGAME_AVAILABLE", False):
            pb = ZyeAudioPlayback()
            self.assertFalse(pb.initialize())

    def test_05_mixer_initialization_failure_handled(self):
        with patch("zye_voice.playback.pygame") as mock_pg:
            mock_pg.mixer.get_init.return_value = False
            mock_pg.mixer.init.side_effect = RuntimeError("No audio device")
            pb = ZyeAudioPlayback()
            self.assertFalse(pb.initialize())

    def test_06_play_mp3_success(self):
        with patch("zye_voice.playback.pygame") as mock_pg:
            mock_pg.mixer.get_init.return_value = True
            busy_states = [True, False]
            mock_pg.mixer.music.get_busy.side_effect = lambda: busy_states.pop(0) if busy_states else False

            pb = ZyeAudioPlayback(PlaybackConfig(poll_interval_seconds=0.01))
            res = self._run(pb.play_mp3(self.mp3_path))
            self.assertTrue(res)
            mock_pg.mixer.music.load.assert_called_once_with(self.mp3_path)
            mock_pg.mixer.music.play.assert_called_once()
            mock_pg.mixer.music.unload.assert_called_once()

    def test_07_play_mp3_nonexistent_file_returns_false(self):
        pb = ZyeAudioPlayback()
        res = self._run(pb.play_mp3("C:/nonexistent_file.mp3"))
        self.assertFalse(res)

    def test_08_playback_stop_cancels_busy_loop(self):
        with patch("zye_voice.playback.pygame") as mock_pg:
            mock_pg.mixer.get_init.return_value = True
            mock_pg.mixer.music.get_busy.return_value = True

            pb = ZyeAudioPlayback(PlaybackConfig(poll_interval_seconds=0.01))

            async def _play_and_stop():
                task = asyncio.create_task(pb.play_mp3(self.mp3_path))
                await asyncio.sleep(0.02)
                await pb.stop()
                return await task

            res = self._run(_play_and_stop())
            self.assertFalse(res)
            mock_pg.mixer.music.stop.assert_called()

    def test_09_concurrent_playback_serialized_by_lock(self):
        with patch("zye_voice.playback.pygame") as mock_pg:
            mock_pg.mixer.get_init.return_value = True
            mock_pg.mixer.music.get_busy.return_value = False

            pb = ZyeAudioPlayback(PlaybackConfig(poll_interval_seconds=0.01))
            order = []

            async def _caller(name):
                await pb.play_mp3(self.mp3_path)
                order.append(name)

            async def _run_concurrent():
                await asyncio.gather(_caller("A"), _caller("B"))

            self._run(_run_concurrent())
            self.assertEqual(len(order), 2)

    def test_10_playback_unload_on_exception(self):
        with patch("zye_voice.playback.pygame") as mock_pg:
            mock_pg.mixer.get_init.return_value = True
            mock_pg.mixer.music.load.side_effect = RuntimeError("Corrupt MP3 header")

            pb = ZyeAudioPlayback()
            res = self._run(pb.play_mp3(self.mp3_path))
            self.assertFalse(res)
            mock_pg.mixer.music.unload.assert_called_once()

    def test_11_close_releases_mixer(self):
        with patch("zye_voice.playback.pygame") as mock_pg:
            mock_pg.mixer.get_init.return_value = True
            pb = ZyeAudioPlayback()
            pb._initialized = True
            self._run(pb.close())
            mock_pg.mixer.quit.assert_called_once()
            self.assertFalse(pb._initialized)

    def test_12_get_status_returns_complete_telemetry(self):
        pb = ZyeAudioPlayback()
        status = pb.get_status()
        self.assertIn("enabled", status)
        self.assertIn("pygame_available", status)
        self.assertIn("mixer_initialized", status)
        self.assertIn("is_playing", status)
        self.assertIn("frequency", status)


if __name__ == "__main__":
    unittest.main(verbosity=2)
