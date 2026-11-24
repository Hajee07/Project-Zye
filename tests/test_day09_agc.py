#!/usr/bin/env python3
"""
ZYE AI — Day 09 AGC Unit Tests
==============================
Tests for zye_audio/agc.py:
  AGCConfig, AGCError, AGCConfigError, AGCResult, AGCProcessor
"""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zye_audio.agc import (
    AGCConfig,
    AGCConfigError,
    AGCError,
    AGCProcessor,
    AGCResult,
)


def _sine(freq: float = 440.0, duration_ms: float = 100.0, amplitude: float = 0.1,
          sample_rate: int = 16000) -> np.ndarray:
    n = int(round(sample_rate * duration_ms / 1000.0))
    t = np.linspace(0, duration_ms / 1000.0, n, endpoint=False, dtype=np.float32)
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)


class TestAGCConfig(unittest.TestCase):

    def test_01_default_config_valid(self):
        cfg = AGCConfig()
        self.assertTrue(cfg.enabled)
        self.assertEqual(cfg.mode, "peak_normalize")
        self.assertAlmostEqual(cfg.target_peak, 0.85)
        self.assertAlmostEqual(cfg.max_gain, 12.0)

    def test_02_adaptive_mode_accepted(self):
        cfg = AGCConfig(mode="adaptive")
        self.assertEqual(cfg.mode, "adaptive")

    def test_03_invalid_mode_raises(self):
        with self.assertRaises(AGCConfigError):
            AGCConfig(mode="invalid_mode")

    def test_04_invalid_target_peak_zero_raises(self):
        with self.assertRaises(AGCConfigError):
            AGCConfig(target_peak=0.0)

    def test_05_invalid_target_peak_over_one_raises(self):
        with self.assertRaises(AGCConfigError):
            AGCConfig(target_peak=1.5)

    def test_06_max_gain_below_one_raises(self):
        with self.assertRaises(AGCConfigError):
            AGCConfig(max_gain=0.9)

    def test_07_limiter_peak_below_target_peak_raises(self):
        with self.assertRaises(AGCConfigError):
            AGCConfig(target_peak=0.85, limiter_peak=0.80)

    def test_08_invalid_sample_rate_raises(self):
        with self.assertRaises(AGCConfigError):
            AGCConfig(sample_rate=-1)

    def test_09_silence_threshold_non_negative(self):
        with self.assertRaises(AGCConfigError):
            AGCConfig(silence_threshold=-0.001)

    def test_10_attack_ms_positive(self):
        with self.assertRaises(AGCConfigError):
            AGCConfig(attack_ms=0.0)

    def test_11_release_ms_positive(self):
        with self.assertRaises(AGCConfigError):
            AGCConfig(release_ms=0.0)


class TestAGCProcessorPeakNorm(unittest.TestCase):

    def setUp(self):
        self.agc = AGCProcessor(AGCConfig(mode="peak_normalize", enabled=True))

    def test_12_silent_input_returns_unchanged(self):
        silent = np.zeros(1600, dtype=np.float32)
        result = self.agc.process(silent)
        self.assertIsInstance(result, AGCResult)
        self.assertEqual(result.status, "SILENCE_PROTECTED")
        self.assertAlmostEqual(result.applied_gain, 1.0)

    def test_13_empty_input_returns_empty_result(self):
        result = self.agc.process(np.array([], dtype=np.float32))
        self.assertEqual(result.status, "EMPTY_INPUT")
        self.assertEqual(len(result.audio), 0)

    def test_14_peak_normalized_to_target(self):
        low = _sine(amplitude=0.05)  # well below target_peak = 0.85
        result = self.agc.process(low)
        self.assertEqual(result.status, "SUCCESS")
        self.assertGreater(result.output_peak, result.input_peak)
        self.assertLessEqual(result.output_peak, 0.96)  # limiter ceiling

    def test_15_loud_signal_not_amplified_beyond_limiter(self):
        loud = _sine(amplitude=0.98)
        result = self.agc.process(loud)
        self.assertLessEqual(result.output_peak, 0.96)

    def test_16_input_array_not_mutated(self):
        orig = _sine(amplitude=0.1)
        copy = orig.copy()
        self.agc.process(orig)
        np.testing.assert_array_equal(orig, copy)

    def test_17_result_is_float32(self):
        sig = _sine(amplitude=0.1)
        result = self.agc.process(sig)
        self.assertEqual(result.audio.dtype, np.float32)

    def test_18_applied_gain_bounded_max(self):
        very_quiet = _sine(amplitude=0.001)
        result = self.agc.process(very_quiet)
        self.assertLessEqual(result.applied_gain, 12.0 + 1e-4)

    def test_19_clipping_detected_flag(self):
        # Artificially force clipping: set gain very high, peak will approach 0.999
        sig = _sine(amplitude=0.1)
        agc = AGCProcessor(AGCConfig(max_gain=12.0, target_peak=0.9999, limiter_peak=1.0))
        result = agc.process(sig)
        # The flag should be True only if output_peak >= 0.999
        if result.output_peak >= 0.999:
            self.assertTrue(result.clipping_detected)

    def test_20_silence_detected_flag(self):
        silent = np.zeros(512, dtype=np.float32)
        result = self.agc.process(silent)
        self.assertTrue(result.silence_detected)

    def test_21_processing_duration_ms_positive(self):
        sig = _sine(amplitude=0.1)
        result = self.agc.process(sig)
        self.assertGreater(result.processing_duration_ms, 0.0)

    def test_22_disabled_config_passthrough(self):
        disabled_agc = AGCProcessor(AGCConfig(enabled=False))
        sig = _sine(amplitude=0.1)
        result = disabled_agc.process(sig)
        self.assertEqual(result.status, "DISABLED")
        np.testing.assert_array_equal(result.audio, sig)

    def test_23_input_rms_always_non_negative(self):
        sig = _sine(amplitude=0.1)
        result = self.agc.process(sig)
        self.assertGreaterEqual(result.input_rms, 0.0)

    def test_24_output_rms_always_non_negative(self):
        sig = _sine(amplitude=0.1)
        result = self.agc.process(sig)
        self.assertGreaterEqual(result.output_rms, 0.0)


class TestAGCProcessorAdaptive(unittest.TestCase):

    def setUp(self):
        self.agc = AGCProcessor(AGCConfig(
            mode="adaptive",
            enabled=True,
            target_rms=0.12,
            attack_ms=10.0,
            release_ms=250.0,
        ))

    def test_25_adaptive_mode_applied(self):
        sig = _sine(amplitude=0.05, duration_ms=200.0)
        result = self.agc.process(sig)
        self.assertEqual(result.mode, "adaptive")

    def test_26_adaptive_amplifies_soft_signal(self):
        sig = _sine(amplitude=0.02, duration_ms=200.0)
        result = self.agc.process(sig)
        self.assertGreater(result.output_rms, result.input_rms)

    def test_27_adaptive_respects_limiter(self):
        sig = _sine(amplitude=0.02, duration_ms=200.0)
        result = self.agc.process(sig)
        self.assertLessEqual(result.output_peak, 0.96)

    def test_28_short_audio_falls_back_to_peak_norm(self):
        # Very short audio (< 1 window = 320 samples at 16kHz with 20ms window)
        short_sig = _sine(amplitude=0.05, duration_ms=10.0)
        result = self.agc.process(short_sig)
        self.assertIn(result.status, ("SUCCESS", "SILENCE_PROTECTED"))

    def test_29_input_immutability_adaptive(self):
        sig = _sine(amplitude=0.05, duration_ms=200.0)
        copy = sig.copy()
        self.agc.process(sig)
        np.testing.assert_array_equal(sig, copy)


class TestAGCPeakLimiter(unittest.TestCase):

    def setUp(self):
        self.agc = AGCProcessor()

    def test_30_peak_limiter_clips_above_ceiling(self):
        loud = np.full(512, 1.5, dtype=np.float32)
        result = self.agc.apply_peak_limiter(loud, limit=0.95)
        self.assertLessEqual(float(np.max(np.abs(result))), 0.95 + 1e-5)

    def test_31_peak_limiter_no_change_if_within_range(self):
        quiet = np.full(512, 0.5, dtype=np.float32)
        result = self.agc.apply_peak_limiter(quiet, limit=0.95)
        np.testing.assert_array_almost_equal(result, quiet)

    def test_32_empty_input_returns_empty(self):
        result = self.agc.apply_peak_limiter(np.array([], dtype=np.float32))
        self.assertEqual(len(result), 0)


class TestAGCDiagnostics(unittest.TestCase):

    def setUp(self):
        self.agc = AGCProcessor()

    def test_33_initial_diagnostics_has_status(self):
        diag = self.agc.get_diagnostics()
        self.assertIn("status", diag)
        self.assertEqual(diag["status"], "ready")

    def test_34_diagnostics_updated_after_process(self):
        sig = _sine(amplitude=0.1)
        self.agc.process(sig)
        diag = self.agc.get_diagnostics()
        self.assertIn("applied_gain", diag)
        self.assertIn("input_peak", diag)
        self.assertIn("output_peak", diag)

    def test_35_total_processed_increments(self):
        sig = _sine(amplitude=0.1)
        before = self.agc.total_processed_frames
        self.agc.process(sig)
        self.assertEqual(self.agc.total_processed_frames, before + 1)

    def test_36_total_silence_increments_on_silent_input(self):
        silent = np.zeros(512, dtype=np.float32)
        before = self.agc.total_silence_events
        self.agc.process(silent)
        self.assertEqual(self.agc.total_silence_events, before + 1)

    def test_37_reset_clears_state(self):
        sig = _sine(amplitude=0.1)
        self.agc.process(sig)
        self.agc.reset()
        self.assertEqual(self.agc.total_processed_frames, 0)
        self.assertEqual(self.agc.total_clipping_events, 0)
        self.assertEqual(self.agc.total_silence_events, 0)
        self.assertEqual(self.agc.last_diagnostics, {})


class TestAGCMathHelpers(unittest.TestCase):

    def setUp(self):
        self.agc = AGCProcessor()

    def test_38_calculate_peak_known_signal(self):
        sig = np.array([0.1, -0.5, 0.3], dtype=np.float32)
        self.assertAlmostEqual(self.agc.calculate_peak(sig), 0.5, places=5)

    def test_39_calculate_rms_known_signal(self):
        # constant amplitude of 1.0 -> RMS = 1.0
        sig = np.ones(1000, dtype=np.float32)
        self.assertAlmostEqual(self.agc.calculate_rms(sig), 1.0, places=5)

    def test_40_calculate_gain_silent_returns_one(self):
        silent = np.zeros(512, dtype=np.float32)
        self.assertAlmostEqual(self.agc.calculate_gain(silent), 1.0, places=5)

    def test_41_calculate_gain_loud_returns_less_than_max(self):
        loud = np.ones(512, dtype=np.float32) * 0.5
        gain = self.agc.calculate_gain(loud)
        self.assertLessEqual(gain, 12.0)

    def test_42_nan_in_input_raises_agc_error(self):
        bad = np.array([float("nan"), 0.5], dtype=np.float32)
        with self.assertRaises(AGCError):
            self.agc.process(bad)

    def test_43_inf_in_input_raises_agc_error(self):
        bad = np.array([float("inf"), 0.5], dtype=np.float32)
        with self.assertRaises(AGCError):
            self.agc.process(bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
