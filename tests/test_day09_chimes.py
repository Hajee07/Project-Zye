#!/usr/bin/env python3
"""
ZYE AI — Day 09 Jarvis Chime Player Unit Tests
===============================================
Tests for zye_audio/chime_player.py:
  ChimeConfig, generate_tone, generate_start_chime, generate_stop_chime,
  JarvisChimePlayer
"""

import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zye_audio.chime_player import (
    ChimeConfig,
    ChimeConfigError,
    JarvisChimePlayer,
    generate_start_chime,
    generate_stop_chime,
    generate_tone,
)


class TestChimeConfig(unittest.TestCase):

    def test_01_default_config_valid(self):
        cfg = ChimeConfig()
        self.assertTrue(cfg.enabled)
        self.assertEqual(cfg.sample_rate, 16000)
        self.assertAlmostEqual(cfg.start_first_frequency, 540.0)
        self.assertAlmostEqual(cfg.start_second_frequency, 820.0)
        self.assertAlmostEqual(cfg.stop_first_frequency, 780.0)
        self.assertAlmostEqual(cfg.stop_second_frequency, 480.0)
        self.assertAlmostEqual(cfg.tone_duration_ms, 75.0)
        self.assertAlmostEqual(cfg.amplitude, 0.12)
        self.assertAlmostEqual(cfg.fade_duration_ms, 12.5)
        self.assertAlmostEqual(cfg.vad_guard_ms, 250.0)
        self.assertEqual(cfg.max_queue_size, 4)

    def test_02_invalid_sample_rate_raises(self):
        with self.assertRaises(ChimeConfigError):
            ChimeConfig(sample_rate=0)

    def test_03_invalid_amplitude_zero_raises(self):
        with self.assertRaises(ChimeConfigError):
            ChimeConfig(amplitude=0.0)

    def test_04_invalid_amplitude_over_one_raises(self):
        with self.assertRaises(ChimeConfigError):
            ChimeConfig(amplitude=1.5)

    def test_05_invalid_tone_duration_zero_raises(self):
        with self.assertRaises(ChimeConfigError):
            ChimeConfig(tone_duration_ms=0.0)

    def test_06_fade_duration_exceeds_half_tone_raises(self):
        with self.assertRaises(ChimeConfigError):
            ChimeConfig(tone_duration_ms=50.0, fade_duration_ms=30.0)

    def test_07_negative_vad_guard_raises(self):
        with self.assertRaises(ChimeConfigError):
            ChimeConfig(vad_guard_ms=-1.0)

    def test_08_invalid_max_queue_size_raises(self):
        with self.assertRaises(ChimeConfigError):
            ChimeConfig(max_queue_size=0)

    def test_09_invalid_frequency_zero_raises(self):
        with self.assertRaises(ChimeConfigError):
            ChimeConfig(start_first_frequency=0.0)

    def test_10_frequency_above_20000_raises(self):
        with self.assertRaises(ChimeConfigError):
            ChimeConfig(start_first_frequency=25000.0)


class TestGenerateTone(unittest.TestCase):

    def setUp(self):
        self.sr = 16000
        self.freq = 440.0
        self.dur_ms = 100.0
        self.amp = 0.12
        self.fade_ms = 12.5

    def test_11_generate_tone_correct_length(self):
        tone = generate_tone(self.freq, self.dur_ms, self.amp, self.sr, self.fade_ms)
        expected_samples = int(round(self.sr * self.dur_ms / 1000.0))
        self.assertEqual(len(tone), expected_samples)

    def test_12_generate_tone_dtype_float32(self):
        tone = generate_tone(self.freq, self.dur_ms, self.amp, self.sr, self.fade_ms)
        self.assertEqual(tone.dtype, np.float32)

    def test_13_generate_tone_max_amplitude_bounded(self):
        tone = generate_tone(self.freq, self.dur_ms, self.amp, self.sr, self.fade_ms)
        self.assertLessEqual(float(np.max(np.abs(tone))), self.amp + 1e-5)

    def test_14_generate_tone_starts_near_zero_fade(self):
        tone = generate_tone(self.freq, self.dur_ms, self.amp, self.sr, self.fade_ms)
        # First sample should be very close to 0 due to fade-in
        self.assertAlmostEqual(float(tone[0]), 0.0, places=5)

    def test_15_generate_tone_ends_near_zero_fade(self):
        tone = generate_tone(self.freq, self.dur_ms, self.amp, self.sr, self.fade_ms)
        # Last sample should be very close to 0 due to fade-out
        self.assertAlmostEqual(float(tone[-1]), 0.0, places=4)

    def test_16_generate_tone_zero_duration_returns_empty(self):
        tone = generate_tone(self.freq, 0.0, self.amp, self.sr, self.fade_ms)
        self.assertEqual(len(tone), 0)

    def test_17_generate_tone_no_fade_still_valid(self):
        tone = generate_tone(self.freq, self.dur_ms, self.amp, self.sr, fade_duration_ms=0.0)
        self.assertEqual(len(tone), int(round(self.sr * self.dur_ms / 1000.0)))

    def test_18_generate_tone_finite_values_only(self):
        tone = generate_tone(self.freq, self.dur_ms, self.amp, self.sr, self.fade_ms)
        self.assertTrue(np.all(np.isfinite(tone)))


class TestGenerateStartStopChimes(unittest.TestCase):

    def test_19_start_chime_length(self):
        cfg = ChimeConfig()
        chime = generate_start_chime(cfg)
        expected = 2 * int(round(cfg.sample_rate * cfg.tone_duration_ms / 1000.0))
        self.assertEqual(len(chime), expected)

    def test_20_stop_chime_length(self):
        cfg = ChimeConfig()
        chime = generate_stop_chime(cfg)
        expected = 2 * int(round(cfg.sample_rate * cfg.tone_duration_ms / 1000.0))
        self.assertEqual(len(chime), expected)

    def test_21_start_chime_dtype_float32(self):
        chime = generate_start_chime()
        self.assertEqual(chime.dtype, np.float32)

    def test_22_stop_chime_dtype_float32(self):
        chime = generate_stop_chime()
        self.assertEqual(chime.dtype, np.float32)

    def test_23_start_chime_amplitude_bounded(self):
        cfg = ChimeConfig(amplitude=0.12)
        chime = generate_start_chime(cfg)
        self.assertLessEqual(float(np.max(np.abs(chime))), cfg.amplitude + 1e-5)

    def test_24_stop_chime_amplitude_bounded(self):
        cfg = ChimeConfig(amplitude=0.12)
        chime = generate_stop_chime(cfg)
        self.assertLessEqual(float(np.max(np.abs(chime))), cfg.amplitude + 1e-5)

    def test_25_start_chime_finite_values(self):
        chime = generate_start_chime()
        self.assertTrue(np.all(np.isfinite(chime)))

    def test_26_stop_chime_finite_values(self):
        chime = generate_stop_chime()
        self.assertTrue(np.all(np.isfinite(chime)))

    def test_27_start_chime_ascending_frequencies(self):
        # Start chime should use 540 Hz then 820 Hz (ascending)
        cfg = ChimeConfig()
        self.assertLess(cfg.start_first_frequency, cfg.start_second_frequency)

    def test_28_stop_chime_descending_frequencies(self):
        # Stop chime should use 780 Hz then 480 Hz (descending)
        cfg = ChimeConfig()
        self.assertGreater(cfg.stop_first_frequency, cfg.stop_second_frequency)

    def test_29_start_chime_custom_sample_rate(self):
        cfg = ChimeConfig(sample_rate=44100)
        chime = generate_start_chime(cfg, sample_rate=44100)
        expected = 2 * int(round(44100 * cfg.tone_duration_ms / 1000.0))
        self.assertEqual(len(chime), expected)


class TestJarvisChimePlayerInit(unittest.TestCase):

    def test_30_player_initializes_with_defaults(self):
        player = JarvisChimePlayer(auto_start=False)
        self.assertFalse(player._running)
        player.close()

    def test_31_player_starts_worker_on_auto_start(self):
        player = JarvisChimePlayer(auto_start=True)
        time.sleep(0.05)
        self.assertTrue(player._worker_thread is not None)
        player.close()

    def test_32_player_start_idempotent(self):
        player = JarvisChimePlayer(auto_start=False)
        player.start()
        player.start()  # second call should be no-op
        self.assertTrue(player._running)
        player.close()

    def test_33_player_stop_graceful(self):
        player = JarvisChimePlayer(auto_start=True)
        time.sleep(0.05)
        player.stop()
        self.assertFalse(player._running)

    def test_34_player_context_manager(self):
        with JarvisChimePlayer(auto_start=True) as player:
            self.assertIsInstance(player, JarvisChimePlayer)
        # After __exit__ the player should be stopped
        self.assertFalse(player._running)


class TestJarvisChimePlayerPlayback(unittest.TestCase):

    def _make_silent_player(self):
        """Create a player with sounddevice stubbed out."""
        cfg = ChimeConfig(enabled=True, vad_guard_ms=50.0)
        player = JarvisChimePlayer(config=cfg, auto_start=False)
        return player

    def test_35_play_start_enqueues_when_enabled(self):
        player = self._make_silent_player()
        player.start()
        with patch.object(player, "_play_waveform_internal", return_value=True):
            result = player.play_start()
        player.close()
        self.assertTrue(result)

    def test_36_play_stop_enqueues_when_enabled(self):
        player = self._make_silent_player()
        player.start()
        with patch.object(player, "_play_waveform_internal", return_value=True):
            result = player.play_stop()
        player.close()
        self.assertTrue(result)

    def test_37_play_disabled_returns_false(self):
        cfg = ChimeConfig(enabled=False)
        player = JarvisChimePlayer(config=cfg, auto_start=False)
        result = player.play("start")
        self.assertFalse(result)
        player.close()

    def test_38_play_unknown_mode_returns_false(self):
        player = self._make_silent_player()
        result = player.play("beep")
        player.close()
        self.assertFalse(result)

    def test_39_queue_full_drops_chime(self):
        cfg = ChimeConfig(max_queue_size=1, enabled=True)
        player = JarvisChimePlayer(config=cfg, auto_start=False)
        player._running = True  # mark as running so play() won't call start()
        # Fill queue manually without starting worker
        player._queue.put(("start", player._start_waveform, 0.15))
        dropped_before = player.dropped_chimes
        result = player.play("start")  # queue is full -> should drop
        player._running = False  # stop cleanly without trying to join thread
        player._worker_thread = None
        self.assertFalse(result)
        self.assertEqual(player.dropped_chimes, dropped_before + 1)

    def test_40_metrics_increment_on_success(self):
        player = self._make_silent_player()
        with patch.object(player, "_play_waveform_internal", return_value=True) as mock_play:
            player.play_start()
            player.play_stop()
            time.sleep(0.1)  # let worker process
        player.close()
        # Both were enqueued; test via mock call count on waveform internal
        self.assertEqual(mock_play.call_count, 2)


class TestChimeFeedbackGuard(unittest.TestCase):

    def test_41_guard_not_active_at_rest(self):
        player = JarvisChimePlayer(auto_start=False)
        self.assertFalse(player.is_chime_guard_active())
        player.close()

    def test_42_guard_active_after_playback_starts(self):
        player = JarvisChimePlayer(auto_start=False)
        # Manually trigger guard
        with player._guard_lock:
            player._guard_until_timestamp = time.perf_counter() + 10.0
        self.assertTrue(player.is_chime_guard_active())
        player.close()

    def test_43_guard_expires_over_time(self):
        player = JarvisChimePlayer(auto_start=False)
        with player._guard_lock:
            player._guard_until_timestamp = time.perf_counter() + 0.05
        time.sleep(0.08)
        self.assertFalse(player.is_chime_guard_active())
        player.close()

    def test_44_guard_remaining_ms_positive_when_active(self):
        player = JarvisChimePlayer(auto_start=False)
        with player._guard_lock:
            player._guard_until_timestamp = time.perf_counter() + 1.0
        self.assertGreater(player.get_guard_remaining_ms(), 0.0)
        player.close()

    def test_45_guard_remaining_ms_zero_when_expired(self):
        player = JarvisChimePlayer(auto_start=False)
        with player._guard_lock:
            player._guard_until_timestamp = time.perf_counter() - 1.0
        self.assertAlmostEqual(player.get_guard_remaining_ms(), 0.0, places=1)
        player.close()


class TestJarvisChimePlayerDiagnostics(unittest.TestCase):

    def test_46_diagnostics_has_all_keys(self):
        player = JarvisChimePlayer(auto_start=False)
        diag = player.get_diagnostics()
        required_keys = [
            "status", "enabled", "sample_rate", "start_first_frequency",
            "start_second_frequency", "stop_first_frequency", "stop_second_frequency",
            "tone_duration_ms", "amplitude", "fade_duration_ms", "vad_guard_ms",
            "guard_active", "guard_remaining_ms", "start_chimes_played",
            "stop_chimes_played", "total_chimes_played", "playback_errors",
            "dropped_chimes", "last_played_mode", "worker_alive", "output_device",
        ]
        for key in required_keys:
            self.assertIn(key, diag, f"Missing key: {key}")
        player.close()

    def test_47_reset_metrics_clears_counters(self):
        player = JarvisChimePlayer(auto_start=False)
        player.start_chimes_played = 5
        player.stop_chimes_played = 3
        player.playback_errors = 1
        player.dropped_chimes = 2
        player.reset_metrics()
        self.assertEqual(player.start_chimes_played, 0)
        self.assertEqual(player.stop_chimes_played, 0)
        self.assertEqual(player.playback_errors, 0)
        self.assertEqual(player.dropped_chimes, 0)
        player.close()

    def test_48_validate_output_device_returns_dict(self):
        player = JarvisChimePlayer(auto_start=False)
        result = player.validate_output_device()
        self.assertIsInstance(result, dict)
        self.assertIn("available", result)
        player.close()

    def test_49_worker_thread_is_daemon(self):
        player = JarvisChimePlayer(auto_start=True)
        time.sleep(0.05)
        if player._worker_thread is not None:
            self.assertTrue(player._worker_thread.daemon)
        player.close()

    def test_50_waveforms_pre_synthesized_on_init(self):
        player = JarvisChimePlayer(auto_start=False)
        self.assertIsInstance(player._start_waveform, np.ndarray)
        self.assertIsInstance(player._stop_waveform, np.ndarray)
        self.assertGreater(len(player._start_waveform), 0)
        self.assertGreater(len(player._stop_waveform), 0)
        player.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
