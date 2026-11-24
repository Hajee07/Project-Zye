#!/usr/bin/env python3
"""
ZYE AI — Day 09 Audio Integration Tests
========================================
Integration tests for AGC and Chime injection into SmartAudioEar:
  - AGCProcessor wired into SmartAudioEar
  - JarvisChimePlayer wired into SmartAudioEar
  - _apply_auto_gain compatibility method
  - get_agc_diagnostics, get_chime_diagnostics, get_audio_enhancement_status
  - get_audio_diagnostics includes Day 09 fields
  - close() tears down both agc and chime_player
  - Feedback guard integration
"""

import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zye_audio.agc import AGCConfig, AGCProcessor
from zye_audio.chime_player import ChimeConfig, JarvisChimePlayer
from zye_audio_ear import AudioConfig, SmartAudioEar, AudioProcessingError


def _make_ear(agc_config: AGCConfig | None = None, chime_config: ChimeConfig | None = None) -> SmartAudioEar:
    """Create a SmartAudioEar in adaptive_rms mode with no neural VAD loading."""
    cfg = AudioConfig(vad_mode="adaptive_rms")
    ear = SmartAudioEar(config=cfg, agc_config=agc_config, chime_config=chime_config)
    return ear


class TestSmartAudioEarDay09Init(unittest.TestCase):

    def test_01_ear_has_agc_attribute(self):
        ear = _make_ear()
        self.assertIsInstance(ear.agc, AGCProcessor)
        ear.close()

    def test_02_ear_has_chime_player_attribute(self):
        ear = _make_ear()
        self.assertIsInstance(ear.chime_player, JarvisChimePlayer)
        ear.close()

    def test_03_custom_agc_config_applied(self):
        agc_cfg = AGCConfig(mode="adaptive", target_rms=0.08)
        ear = _make_ear(agc_config=agc_cfg)
        self.assertEqual(ear.agc.config.mode, "adaptive")
        self.assertAlmostEqual(ear.agc.config.target_rms, 0.08)
        ear.close()

    def test_04_custom_chime_config_applied(self):
        chime_cfg = ChimeConfig(enabled=False)
        ear = _make_ear(chime_config=chime_cfg)
        self.assertFalse(ear.chime_player.config.enabled)
        ear.close()

    def test_05_default_agc_config_matches_spec(self):
        ear = _make_ear()
        self.assertAlmostEqual(ear.agc.config.target_peak, 0.85)
        self.assertAlmostEqual(ear.agc.config.max_gain, 12.0)
        self.assertAlmostEqual(ear.agc.config.limiter_peak, 0.95)
        ear.close()

    def test_06_default_chime_config_matches_spec(self):
        ear = _make_ear()
        self.assertAlmostEqual(ear.chime_player.config.start_first_frequency, 540.0)
        self.assertAlmostEqual(ear.chime_player.config.start_second_frequency, 820.0)
        self.assertAlmostEqual(ear.chime_player.config.stop_first_frequency, 780.0)
        self.assertAlmostEqual(ear.chime_player.config.stop_second_frequency, 480.0)
        ear.close()


class TestSmartAudioEarApplyAutoGain(unittest.TestCase):

    def test_07_apply_auto_gain_returns_ndarray(self):
        ear = _make_ear()
        t = np.linspace(0, 0.1, 1600, dtype=np.float32)
        sig = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        result = ear._apply_auto_gain(sig)
        self.assertIsInstance(result, np.ndarray)
        ear.close()

    def test_08_apply_auto_gain_output_bounded(self):
        ear = _make_ear()
        t = np.linspace(0, 0.1, 1600, dtype=np.float32)
        sig = (0.05 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        result = ear._apply_auto_gain(sig)
        self.assertLessEqual(float(np.max(np.abs(result))), 0.96)
        ear.close()

    def test_09_apply_auto_gain_does_not_mutate_input(self):
        ear = _make_ear()
        sig = np.random.uniform(-0.1, 0.1, 800).astype(np.float32)
        copy = sig.copy()
        ear._apply_auto_gain(sig)
        np.testing.assert_array_equal(sig, copy)
        ear.close()

    def test_10_apply_auto_gain_silent_passthrough(self):
        ear = _make_ear()
        silent = np.zeros(512, dtype=np.float32)
        result = ear._apply_auto_gain(silent)
        np.testing.assert_array_equal(result, silent)
        ear.close()


class TestSmartAudioEarDiagnostics(unittest.TestCase):

    def test_11_get_agc_diagnostics_returns_dict(self):
        ear = _make_ear()
        diag = ear.get_agc_diagnostics()
        self.assertIsInstance(diag, dict)
        self.assertIn("enabled", diag)
        self.assertIn("mode", diag)
        ear.close()

    def test_12_get_chime_diagnostics_returns_dict(self):
        ear = _make_ear()
        diag = ear.get_chime_diagnostics()
        self.assertIsInstance(diag, dict)
        self.assertIn("enabled", diag)
        self.assertIn("total_chimes_played", diag)
        ear.close()

    def test_13_get_audio_enhancement_status_returns_dict(self):
        ear = _make_ear()
        status = ear.get_audio_enhancement_status()
        self.assertIsInstance(status, dict)
        self.assertIn("status", status)
        self.assertEqual(status["status"], "DAY_09_AUDIO_ENHANCEMENT_READY")
        self.assertIn("agc", status)
        self.assertIn("chimes", status)
        ear.close()

    def test_14_get_audio_diagnostics_has_day09_fields(self):
        ear = _make_ear()
        diag = ear.get_audio_diagnostics()
        self.assertIn("agc_status", diag)
        self.assertIn("chime_status", diag)
        self.assertIn("audio_enhancement_status", diag)
        ear.close()

    def test_15_get_audio_diagnostics_has_day07_status(self):
        ear = _make_ear()
        diag = ear.get_audio_diagnostics()
        self.assertEqual(diag.get("diagnostic_status"), "DAY_07_AUDIO_EAR_READY")
        ear.close()

    def test_16_get_audio_diagnostics_has_day08_status(self):
        ear = _make_ear()
        diag = ear.get_audio_diagnostics()
        self.assertIn("neural_vad_status", diag)
        ear.close()


class TestSmartAudioEarClose(unittest.TestCase):

    def test_17_close_stops_chime_player(self):
        ear = _make_ear()
        ear.close()
        self.assertFalse(ear.chime_player._running)

    def test_18_close_resets_agc_counters(self):
        ear = _make_ear()
        # Process some signal
        t = np.linspace(0, 0.1, 1600, dtype=np.float32)
        sig = (0.05 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        ear._apply_auto_gain(sig)
        ear.close()
        # After close, AGC counters should be reset
        self.assertEqual(ear.agc.total_processed_frames, 0)

    def test_19_double_close_safe(self):
        ear = _make_ear()
        ear.close()
        try:
            ear.close()
        except Exception as exc:
            self.fail(f"Double close raised an exception: {exc}")

    def test_20_context_manager_on_smart_audio_ear(self):
        ear = _make_ear()
        # SmartAudioEar doesn't implement __enter__/__exit__ but close() should work
        ear.close()
        self.assertFalse(ear.chime_player._running)


class TestChimeFeedbackGuardIntegration(unittest.TestCase):

    def test_21_guard_not_active_before_any_chime(self):
        ear = _make_ear()
        self.assertFalse(ear.chime_player.is_chime_guard_active())
        ear.close()

    def test_22_guard_active_after_play(self):
        ear = _make_ear()
        # Manually trigger guard window
        with ear.chime_player._guard_lock:
            ear.chime_player._guard_until_timestamp = time.perf_counter() + 10.0
        self.assertTrue(ear.chime_player.is_chime_guard_active())
        ear.close()

    def test_23_guard_expires(self):
        ear = _make_ear()
        with ear.chime_player._guard_lock:
            ear.chime_player._guard_until_timestamp = time.perf_counter() + 0.05
        time.sleep(0.08)
        self.assertFalse(ear.chime_player.is_chime_guard_active())
        ear.close()

    def test_24_chime_enabled_flag_respects_config(self):
        chime_cfg = ChimeConfig(enabled=False)
        ear = _make_ear(chime_config=chime_cfg)
        self.assertFalse(ear.chime_player.config.enabled)
        ear.close()


class TestAGCIntegrationWithAudio(unittest.TestCase):

    def test_25_agc_amplifies_soft_signal(self):
        ear = _make_ear()
        t = np.linspace(0, 0.5, 8000, dtype=np.float32)
        soft = (0.01 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        result = ear._apply_auto_gain(soft)
        self.assertGreater(float(np.max(np.abs(result))), float(np.max(np.abs(soft))))
        ear.close()

    def test_26_agc_does_not_exceed_limiter_on_loud_signal(self):
        ear = _make_ear()
        t = np.linspace(0, 0.5, 8000, dtype=np.float32)
        loud = (0.98 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        result = ear._apply_auto_gain(loud)
        self.assertLessEqual(float(np.max(np.abs(result))), 0.96)
        ear.close()

    def test_27_agc_no_effect_on_silence(self):
        ear = _make_ear()
        silent = np.zeros(1600, dtype=np.float32)
        result = ear._apply_auto_gain(silent)
        np.testing.assert_array_equal(result, silent)
        ear.close()

    def test_28_agc_total_processed_increments_through_apply(self):
        ear = _make_ear()
        t = np.linspace(0, 0.1, 1600, dtype=np.float32)
        sig = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        before = ear.agc.total_processed_frames
        ear._apply_auto_gain(sig)
        self.assertEqual(ear.agc.total_processed_frames, before + 1)
        ear.close()

    def test_29_agc_configured_in_peak_normalize_mode_by_default(self):
        ear = _make_ear()
        self.assertEqual(ear.agc.config.mode, "peak_normalize")
        ear.close()

    def test_30_chime_player_worker_thread_named(self):
        ear = _make_ear()
        time.sleep(0.05)
        if ear.chime_player._worker_thread is not None:
            self.assertEqual(ear.chime_player._worker_thread.name, "ZyeChimePlayerWorker")
        ear.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
