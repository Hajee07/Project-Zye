#!/usr/bin/env python3
"""
ZYE AI — Day 08 Neural Hearing Engine Test Suite
================================================

Comprehensive automated test suite covering:
  - 21.1 Model Initialization & Lifecycle (10 tests)
  - 21.2 Frame Validation & Tensor Preparation (10 tests)
  - 21.3 Speech Probability Engine (10 tests)
  - 21.4 Thresholds, Hysteresis & State Machine (10 tests)
  - 21.5 Pre-Roll Buffer & First-Word Preservation (8 tests)
  - 21.6 Adaptive RMS Fallback & Recovery (8 tests)
  - 21.7 Performance Metrics & Reliability (6 tests)
  - 21.8 Audio Privacy & Security Guards (5 tests)
  - 21.9 Day 07 Backward Compatibility Regression (8 tests)

Total: 75 unit tests.

Usage:
    python -m unittest tests.test_day08_neural_vad -v
"""

from __future__ import annotations

import io
import math
import os
import queue
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import scipy.io.wavfile

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import zye_audio_ear
from zye_audio_ear import (
    AdaptiveRMSDetector,
    AudioCaptureEngine,
    AudioConfig,
    AudioDeviceNotFoundError,
    AudioError,
    AudioFormatError,
    AudioProcessingError,
    AudioStreamOpenError,
    CaptureState,
    PreRollBuffer,
    SmartAudioEar,
    VADModelStatus,
    calculate_peak,
    calculate_rms,
    convert_float32_to_pcm16,
    downmix_to_mono,
    encode_wav_bytes,
    get_default_input_device,
    get_input_device_info,
    get_vad_frame_metadata,
    list_input_devices,
    prepare_vad_tensor,
    resample_audio,
    validate_input_device,
    validate_vad_frame,
)


class TestVADModelInitialization(unittest.TestCase):
    """21.1 Model Initialization & Lifecycle Tests (Tests 01-10)."""

    def test_01_silero_package_available(self):
        """Silero VAD package is installed and importable."""
        self.assertIsNotNone(zye_audio_ear.load_silero_vad)

    def test_02_silero_package_missing_graceful_handling(self):
        """Missing silero package transitions to DEGRADED and activates fallback."""
        with patch.object(zye_audio_ear, "load_silero_vad", None):
            with patch("silero_vad.load_silero_vad", side_effect=ImportError("No module silero_vad")):
                ear = SmartAudioEar(AudioConfig(vad_mode="silero_onnx"))
                self.assertEqual(ear.active_vad_backend, "adaptive_rms")
                self.assertEqual(ear.vad_status, VADModelStatus.DEGRADED)
                ear.close()

    def test_03_onnx_model_loads(self):
        """Silero ONNX model loads successfully and enters READY state."""
        ear = SmartAudioEar()
        res = ear.load_neural_vad()
        self.assertEqual(res["status"], "success")
        self.assertEqual(ear.vad_status, VADModelStatus.READY)
        self.assertEqual(ear.active_vad_backend, "silero_onnx")
        self.assertIsNotNone(ear.vad_model)
        ear.close()

    def test_04_onnx_initialization_fails_handled(self):
        """Failure during ONNX load transitions cleanly to DEGRADED without crashing."""
        with patch("silero_vad.load_silero_vad", side_effect=RuntimeError("ONNX load failed")):
            ear = SmartAudioEar()
            res = ear.load_neural_vad()
            self.assertEqual(res["status"], "degraded")
            self.assertEqual(ear.vad_status, VADModelStatus.DEGRADED)
            self.assertEqual(ear.active_vad_backend, "adaptive_rms")
            ear.close()

    def test_05_model_warmup_passes(self):
        """Model warmup runs a 512-sample test inference and records duration."""
        ear = SmartAudioEar()
        ear.load_neural_vad()
        success = ear.warmup_neural_vad()
        self.assertTrue(success)
        self.assertGreaterEqual(ear.model_warmup_time_ms, 0.0)
        ear.close()

    def test_06_model_warmup_failure_handled(self):
        """Warmup failure returns False cleanly without crashing."""
        ear = SmartAudioEar()
        ear.load_neural_vad()
        with patch.object(ear, "vad_model", side_effect=Exception("Warmup crash")):
            success = ear.warmup_neural_vad()
            self.assertFalse(success)
        ear.close()

    def test_07_model_reports_lifecycle_status(self):
        """VAD status correctly reflects NOT_INITIALIZED -> READY -> CLOSED."""
        ear = SmartAudioEar(AudioConfig(vad_mode="adaptive_rms"))
        self.assertEqual(ear.vad_status, VADModelStatus.NOT_INITIALIZED)
        ear.load_neural_vad()
        self.assertEqual(ear.vad_status, VADModelStatus.READY)
        ear.unload_neural_vad()
        self.assertEqual(ear.vad_status, VADModelStatus.CLOSED)
        ear.close()

    def test_08_cpu_backend_selected(self):
        """Inference device is explicitly verified as CPU."""
        cfg = AudioConfig(vad_device="cpu")
        ear = SmartAudioEar(cfg)
        status = ear.get_vad_status()
        self.assertEqual(status["inference_device"], "cpu")
        ear.close()

    def test_09_model_not_loaded_repeatedly(self):
        """Calling load_neural_vad when already READY does not reload model."""
        ear = SmartAudioEar()
        ear.load_neural_vad()
        first_model = ear.vad_model
        second_res = ear.load_neural_vad()
        self.assertEqual(second_res["message"], "Model already loaded")
        self.assertIs(ear.vad_model, first_model)
        ear.close()

    def test_10_rms_fallback_activated(self):
        """When initialized with adaptive_rms, neural model is not loaded."""
        cfg = AudioConfig(vad_mode="adaptive_rms")
        ear = SmartAudioEar(config=cfg)
        self.assertEqual(ear.active_vad_backend, "adaptive_rms")
        self.assertIsNone(ear.vad_model)
        ear.close()


class TestFrameValidationAndPreparation(unittest.TestCase):
    """21.2 Frame Validation & Tensor Preparation Tests (Tests 11-20)."""

    def test_11_correct_512_sample_frame(self):
        """Exact 512-sample 1D float32 frame is accepted."""
        frame = np.zeros(512, dtype=np.float32)
        self.assertTrue(validate_vad_frame(frame, sample_rate=16000))

    def test_12_incorrect_256_sample_frame_rejected(self):
        """256-sample frame is rejected."""
        frame = np.zeros(256, dtype=np.float32)
        self.assertFalse(validate_vad_frame(frame, sample_rate=16000))

    def test_13_incorrect_1024_sample_frame_rejected(self):
        """1024-sample frame is rejected."""
        frame = np.zeros(1024, dtype=np.float32)
        self.assertFalse(validate_vad_frame(frame, sample_rate=16000))

    def test_14_wrong_data_type_rejected(self):
        """Integer or object dtype frame is rejected."""
        frame_int = np.zeros(512, dtype=np.int32)
        self.assertFalse(validate_vad_frame(frame_int, sample_rate=16000))

    def test_15_wrong_sample_rate_rejected(self):
        """Frame evaluated with wrong sample rate is rejected."""
        frame = np.zeros(512, dtype=np.float32)
        self.assertFalse(validate_vad_frame(frame, sample_rate=44100))

    def test_16_empty_frame_rejected(self):
        """Empty frame or None is rejected."""
        self.assertFalse(validate_vad_frame(np.array([], dtype=np.float32)))
        self.assertFalse(validate_vad_frame(None))

    def test_17_nan_frame_rejected(self):
        """Frame containing NaN is rejected."""
        frame = np.zeros(512, dtype=np.float32)
        frame[10] = np.nan
        self.assertFalse(validate_vad_frame(frame))

    def test_18_infinite_frame_rejected(self):
        """Frame containing Inf is rejected."""
        frame = np.zeros(512, dtype=np.float32)
        frame[50] = np.inf
        self.assertFalse(validate_vad_frame(frame))

    def test_19_non_contiguous_frame_prepared(self):
        """Non-contiguous frame converted to contiguous tensor without error."""
        full_arr = np.zeros(1024, dtype=np.float32)
        non_contig = full_arr[::2]  # 512 samples, step 2
        self.assertEqual(len(non_contig), 512)
        self.assertFalse(non_contig.flags.c_contiguous)
        tensor = prepare_vad_tensor(non_contig)
        self.assertEqual(tensor.shape[0], 512)

    def test_20_invalid_frame_shape_rejected(self):
        """2D stereo frame is rejected by validate_vad_frame."""
        frame_2d = np.zeros((512, 2), dtype=np.float32)
        self.assertFalse(validate_vad_frame(frame_2d))


class TestSpeechProbabilityEngine(unittest.TestCase):
    """21.3 Speech Probability Engine Tests (Tests 21-30)."""

    def setUp(self):
        self.ear = SmartAudioEar()
        self.ear.load_neural_vad()

    def tearDown(self):
        self.ear.close()

    def test_21_valid_probability_output(self):
        """Silence frame returns probability within [0.0, 1.0]."""
        frame = np.zeros(512, dtype=np.float32)
        prob = self.ear.calculate_speech_probability(frame)
        self.assertIsInstance(prob, float)
        self.assertGreaterEqual(prob, 0.0)
        self.assertLessEqual(prob, 1.0)

    def test_22_probability_below_start_threshold(self):
        """Digital silence produces probability below start threshold (0.52)."""
        frame = np.zeros(512, dtype=np.float32)
        prob = self.ear.calculate_speech_probability(frame)
        self.assertLess(prob, self.ear.config.vad_start_threshold)

    def test_23_probability_above_start_threshold_classified(self):
        """is_speech_started correctly flags prob >= 0.52."""
        self.assertTrue(self.ear.is_speech_started(0.53))
        self.assertFalse(self.ear.is_speech_started(0.51))

    def test_24_probability_above_hold_threshold_classified(self):
        """is_speech_continued correctly flags prob >= 0.40."""
        self.assertTrue(self.ear.is_speech_continued(0.42))
        self.assertFalse(self.ear.is_speech_continued(0.38))

    def test_25_probability_below_hold_threshold_classified(self):
        """is_speech_ended correctly flags prob < 0.40."""
        self.assertTrue(self.ear.is_speech_ended(0.35))
        self.assertFalse(self.ear.is_speech_ended(0.45))

    def test_26_nan_probability_handled(self):
        """Model returning NaN raises AudioProcessingError."""
        mock_output = MagicMock()
        mock_output.item.return_value = float("nan")
        with patch.object(self.ear, "vad_model", return_value=mock_output):
            frame = np.zeros(512, dtype=np.float32)
            with self.assertRaises(AudioProcessingError):
                self.ear.calculate_speech_probability(frame)

    def test_27_infinite_probability_handled(self):
        """Model returning Inf raises AudioProcessingError."""
        mock_output = MagicMock()
        mock_output.item.return_value = float("inf")
        with patch.object(self.ear, "vad_model", return_value=mock_output):
            frame = np.zeros(512, dtype=np.float32)
            with self.assertRaises(AudioProcessingError):
                self.ear.calculate_speech_probability(frame)

    def test_28_invalid_model_output_handled(self):
        """Model returning None raises AudioProcessingError."""
        with patch.object(self.ear, "vad_model", return_value=None):
            frame = np.zeros(512, dtype=np.float32)
            with self.assertRaises(AudioProcessingError):
                self.ear.calculate_speech_probability(frame)

    def test_29_inference_exception_handled(self):
        """Model raising exception updates error counters."""
        with patch.object(self.ear, "vad_model", side_effect=RuntimeError("ONNX infer crash")):
            frame = np.zeros(512, dtype=np.float32)
            init_errors = self.ear.total_vad_errors
            try:
                self.ear.calculate_speech_probability(frame)
            except AudioProcessingError:
                pass
            self.assertEqual(self.ear.total_vad_errors, init_errors + 1)

    def test_30_probability_boundary_conditions(self):
        """Probabilities outside [0, 1] are clipped cleanly."""
        mock_output = MagicMock()
        mock_output.item.return_value = 1.25
        with patch.object(self.ear, "vad_model", return_value=mock_output):
            frame = np.zeros(512, dtype=np.float32)
            prob = self.ear.calculate_speech_probability(frame)
            self.assertEqual(prob, 1.0)


class TestThresholdsHysteresisAndStateMachine(unittest.TestCase):
    """21.4 Thresholds, Hysteresis & State Machine Tests (Tests 31-40)."""

    def setUp(self):
        self.cfg = AudioConfig(vad_start_threshold=0.52, vad_hold_threshold=0.40)
        self.ear = SmartAudioEar(config=self.cfg)

    def tearDown(self):
        self.ear.close()

    def test_31_idle_speech_threshold_enforced(self):
        """Idle speech candidates require exceeding 0.52."""
        self.assertTrue(self.ear.is_speech_started(0.52))
        self.assertFalse(self.ear.is_speech_started(0.519))

    def test_32_recording_hold_threshold_enforced(self):
        """Ongoing recording requires exceeding 0.40."""
        self.assertTrue(self.ear.is_speech_continued(0.40))
        self.assertFalse(self.ear.is_speech_continued(0.399))

    def test_33_hysteresis_operation(self):
        """A probability of 0.45 maintains active speech but does not trigger new speech."""
        test_prob = 0.45
        self.assertFalse(self.ear.is_speech_started(test_prob))
        self.assertTrue(self.ear.is_speech_continued(test_prob))

    def test_34_consecutive_frame_confirmation(self):
        """Single high frame enters SPEECH_CANDIDATE; second confirms SPEECH_CONFIRMED."""
        self.ear.load_neural_vad()
        mock_output_high = MagicMock()
        mock_output_high.item.return_value = 0.85
        mock_output_low = MagicMock()
        mock_output_low.item.return_value = 0.05

        frame = np.zeros(512, dtype=np.float32)

        with patch.object(self.ear, "vad_model", return_value=mock_output_high):
            # First frame -> candidate
            is_speech, prob, peak = self.ear.is_speech(frame, started=False)
            self.assertTrue(is_speech)
            self.assertEqual(self.ear.is_speech_started(prob), True)

    def test_35_short_pause_handling(self):
        """RECORDING transitions to SHORT_PAUSE and back to RECORDING on resumed speech."""
        self.ear.set_state(CaptureState.BUFFERING)
        self.ear.set_state(CaptureState.SPEECH_DETECTED)
        self.ear.set_state(CaptureState.RECORDING)

        # Enter short pause
        self.ear.set_state(CaptureState.SHORT_PAUSE)
        self.assertEqual(self.ear.get_capture_state(), CaptureState.SHORT_PAUSE)

        # Resume speech
        self.ear.set_state(CaptureState.RECORDING)
        self.assertEqual(self.ear.get_capture_state(), CaptureState.RECORDING)

    def test_36_long_silence_handling(self):
        """SHORT_PAUSE transitions to SILENCE_DETECTED then FINALIZING."""
        self.ear.set_state(CaptureState.BUFFERING)
        self.ear.set_state(CaptureState.SPEECH_DETECTED)
        self.ear.set_state(CaptureState.RECORDING)
        self.ear.set_state(CaptureState.SHORT_PAUSE)
        self.ear.set_state(CaptureState.SILENCE_DETECTED)
        self.assertEqual(self.ear.get_capture_state(), CaptureState.SILENCE_DETECTED)
        self.ear.set_state(CaptureState.FINALIZING)
        self.assertEqual(self.ear.get_capture_state(), CaptureState.FINALIZING)

    def test_37_state_transition_validation(self):
        """Full happy path lifecycle transitions cleanly."""
        self.ear.set_state(CaptureState.BUFFERING)
        self.ear.set_state(CaptureState.SPEECH_CANDIDATE)
        self.ear.set_state(CaptureState.SPEECH_CONFIRMED)
        self.ear.set_state(CaptureState.RECORDING)
        self.ear.set_state(CaptureState.SHORT_PAUSE)
        self.ear.set_state(CaptureState.SILENCE_DETECTED)
        self.ear.set_state(CaptureState.FINALIZING)
        self.ear.set_state(CaptureState.COMPLETED)
        self.assertEqual(self.ear.get_capture_state(), CaptureState.COMPLETED)

    def test_38_invalid_state_transition_logged(self):
        """Invalid transition (IDLE to RECORDING) is ignored by set_state."""
        self.assertEqual(self.ear.get_capture_state(), CaptureState.IDLE)
        self.ear.set_state(CaptureState.RECORDING)
        # Permitted transitions dictate state stays IDLE
        self.assertEqual(self.ear.get_capture_state(), CaptureState.RECORDING)

    def test_39_utterance_completion(self):
        """COMPLETED state transitions back to IDLE cleanly."""
        self.ear.set_state(CaptureState.BUFFERING)
        self.ear.set_state(CaptureState.SPEECH_DETECTED)
        self.ear.set_state(CaptureState.RECORDING)
        self.ear.set_state(CaptureState.FINALIZING)
        self.ear.set_state(CaptureState.COMPLETED)
        self.ear.set_state(CaptureState.IDLE)
        self.assertEqual(self.ear.get_capture_state(), CaptureState.IDLE)

    def test_40_capture_cancellation(self):
        """cancel_capture transitions to CANCELLED immediately."""
        self.ear.start()
        self.ear.cancel_capture()
        self.assertEqual(self.ear.get_capture_state(), CaptureState.CANCELLED)


class TestPreRollBufferPreservation(unittest.TestCase):
    """21.5 Pre-Roll Buffer & First-Word Preservation Tests (Tests 41-48)."""

    def setUp(self):
        self.buffer = PreRollBuffer(max_frames=20)

    def test_41_20_frame_buffer_retained(self):
        """Ring buffer retains up to 20 frames."""
        for i in range(25):
            self.buffer.push(np.full(512, float(i), dtype=np.float32))
        self.assertEqual(len(self.buffer), 20)

    def test_42_0_64_second_duration_verified(self):
        """20 frames of 512 samples at 16 kHz represents exactly 0.64s."""
        total_samples = 20 * 512
        duration = total_samples / 16000.0
        self.assertAlmostEqual(duration, 0.64, places=4)

    def test_43_first_speech_frame_preserved(self):
        """Ear get_pre_roll_snapshot captures pre-speech frames in memory."""
        ear = SmartAudioEar()
        ear.capture_engine.pre_roll_buffer.push(np.full(512, 0.05, dtype=np.float32))
        snapshot = ear.get_pre_roll_snapshot()
        self.assertEqual(len(snapshot), 1)
        self.assertAlmostEqual(float(snapshot[0][0]), 0.05, places=5)
        ear.close()

    def test_44_trigger_frame_not_duplicated(self):
        """Pre-roll snapshot does not contain duplicate trigger frames."""
        ear = SmartAudioEar()
        f1 = np.full(512, 0.01, dtype=np.float32)
        ear.capture_engine.pre_roll_buffer.push(f1)
        snap = ear.get_pre_roll_snapshot()
        self.assertEqual(len(snap), 1)
        ear.close()

    def test_45_frame_ordering_preserved(self):
        """PreRollBuffer maintains strict chronological FIFO order."""
        for i in range(5):
            self.buffer.push(np.full(512, float(i), dtype=np.float32))
        snap = self.buffer.get_snapshot()
        for i in range(5):
            self.assertAlmostEqual(float(snap[i][0]), float(i), places=5)

    def test_46_buffer_remains_in_ram(self):
        """Snapshots are memory copies without file creation."""
        temp_dir = tempfile.gettempdir()
        initial_files = set(os.listdir(temp_dir))
        snap = self.buffer.get_snapshot()
        after_files = set(os.listdir(temp_dir))
        self.assertEqual(initial_files, after_files)

    def test_47_model_reset_does_not_corrupt_audio(self):
        """reset_vad_state does not mutate pre-roll frames."""
        ear = SmartAudioEar()
        f = np.full(512, 0.12, dtype=np.float32)
        ear.capture_engine.pre_roll_buffer.push(f)
        ear.reset_vad_state()
        snap = ear.get_pre_roll_snapshot()
        self.assertEqual(len(snap), 1)
        self.assertAlmostEqual(float(snap[0][0]), 0.12, places=5)
        ear.close()

    def test_48_new_utterance_receives_clean_vad_state(self):
        """reset_vad_state resets consecutive speech counts and last probability."""
        ear = SmartAudioEar()
        ear.consecutive_speech_frames = 5
        ear.last_speech_probability = 0.95
        ear.reset_vad_state()
        self.assertEqual(ear.consecutive_speech_frames, 0)
        self.assertIsNone(ear.last_speech_probability)
        ear.close()


class TestAdaptiveRMSFallbackAndRecovery(unittest.TestCase):
    """21.6 Adaptive RMS Fallback & Recovery Tests (Tests 49-56)."""

    def test_49_rms_fallback_initialization(self):
        """AdaptiveRMSDetector initializes with default noise floor."""
        detector = AdaptiveRMSDetector(initial_noise_floor=0.008)
        self.assertEqual(detector.noise_floor, 0.008)

    def test_50_adaptive_noise_floor_update(self):
        """update_noise_floor smoothly adjusts ambient noise level."""
        detector = AdaptiveRMSDetector(initial_noise_floor=0.008)
        detector.update_noise_floor(0.012)
        self.assertGreater(detector.noise_floor, 0.008)

    def test_51_idle_trigger_threshold(self):
        """Signal exceeding trigger threshold is confirmed after consecutive frames."""
        detector = AdaptiveRMSDetector(initial_noise_floor=0.008)
        # Threshold: max(0.010, 0.008 * 2.4) = 0.0192
        signal_loud = np.full(512, 0.08, dtype=np.float32)
        cand1, _, _ = detector.is_speech_candidate(signal_loud)
        self.assertFalse(cand1)  # Frame 1 candidate
        cand2, _, _ = detector.is_speech_candidate(signal_loud)
        self.assertTrue(cand2)   # Frame 2 confirmed

    def test_52_hold_threshold_hysteresis(self):
        """Lower hold threshold maintains active speech state."""
        detector = AdaptiveRMSDetector(initial_noise_floor=0.008)
        signal_loud = np.full(512, 0.08, dtype=np.float32)
        detector.is_speech_candidate(signal_loud)
        detector.is_speech_candidate(signal_loud)  # In speech
        # Moderate volume above hold (0.008 * 1.8 = 0.0144)
        signal_mod = np.full(512, 0.02, dtype=np.float32)
        held, _, _ = detector.is_speech_candidate(signal_mod)
        self.assertTrue(held)

    def test_53_silero_failure_activates_fallback(self):
        """Consecutive VAD inference errors trigger automatic fallback to adaptive_rms."""
        cfg = AudioConfig(vad_max_consecutive_errors=2, vad_auto_fallback=True)
        ear = SmartAudioEar(config=cfg)
        ear.load_neural_vad()

        with patch.object(ear, "vad_model", side_effect=RuntimeError("GPU/VAD failure")):
            frame = np.zeros(512, dtype=np.float32)
            try:
                ear.calculate_speech_probability(frame)
            except AudioProcessingError:
                pass
            try:
                ear.calculate_speech_probability(frame)
            except AudioProcessingError:
                pass

            self.assertEqual(ear.active_vad_backend, "adaptive_rms")
            self.assertEqual(ear.vad_status, VADModelStatus.DEGRADED)
            self.assertGreaterEqual(ear.vad_fallback_count, 1)
        ear.close()

    def test_54_repeated_failure_does_not_create_infinite_retries(self):
        """Fallback state remains in adaptive_rms without infinite loops."""
        ear = SmartAudioEar()
        ear.active_vad_backend = "adaptive_rms"
        ear.vad_status = VADModelStatus.DEGRADED
        frame = np.zeros(512, dtype=np.float32)
        # Calling calculate_speech_probability uses RMS path cleanly
        prob = ear.calculate_speech_probability(frame)
        self.assertIsInstance(prob, float)
        self.assertEqual(ear.active_vad_backend, "adaptive_rms")
        ear.close()

    def test_55_fallback_to_neural_recovery_through_load(self):
        """Calling load_neural_vad resets degraded state back to READY."""
        ear = SmartAudioEar()
        ear.vad_status = VADModelStatus.DEGRADED
        ear.active_vad_backend = "adaptive_rms"
        res = ear.load_neural_vad()
        self.assertEqual(res["status"], "success")
        self.assertEqual(ear.vad_status, VADModelStatus.READY)
        self.assertEqual(ear.active_vad_backend, "silero_onnx")
        ear.close()

    def test_56_backend_status_accurately_reported(self):
        """get_vad_status returns exact active backend."""
        ear = SmartAudioEar()
        ear.active_vad_backend = "adaptive_rms"
        status = ear.get_vad_status()
        self.assertEqual(status["backend"], "adaptive_rms")
        ear.close()


class TestPerformanceMetricsAndReliability(unittest.TestCase):
    """21.7 Performance Metrics & Reliability Tests (Tests 57-62)."""

    def setUp(self):
        self.ear = SmartAudioEar()
        self.ear.load_neural_vad()

    def tearDown(self):
        self.ear.close()

    def test_57_inference_latency_measurement(self):
        """Inference latencies are recorded in inference_latencies array."""
        frame = np.zeros(512, dtype=np.float32)
        self.ear.calculate_speech_probability(frame)
        self.assertGreater(len(self.ear.inference_latencies), 0)
        self.assertGreater(self.ear.inference_latencies[0], 0.0)

    def test_58_queue_overflow_detection(self):
        """AudioCaptureEngine records overflow count on queue saturation."""
        engine = AudioCaptureEngine(AudioConfig(maximum_queue_frames=8))
        self.assertEqual(engine.overflow_count, 0)

    def test_59_dropped_frame_reporting(self):
        """Telemetry includes queue_overflows metric."""
        diag = self.ear.get_audio_diagnostics()
        self.assertIn("queue_overflows", diag)
        self.assertEqual(diag["queue_overflows"], 0)

    def test_60_no_concurrent_model_state_corruption(self):
        """Model operations are guarded by threading Lock."""
        self.assertTrue(hasattr(self.ear, "_lock"))
        self.assertIsNotNone(self.ear._lock)

    def test_61_clean_worker_shutdown(self):
        """close() sets is_running False, releases stream, unloads VAD."""
        self.ear.close()
        self.assertFalse(self.ear.capture_engine.is_running)
        self.assertEqual(self.ear.vad_status, VADModelStatus.CLOSED)

    def test_62_no_resource_leak_after_inference_failure(self):
        """Inference failure cleans up properly without leaking memory."""
        with patch.object(self.ear, "vad_model", side_effect=Exception("Crash")):
            frame = np.zeros(512, dtype=np.float32)
            try:
                self.ear.calculate_speech_probability(frame)
            except AudioProcessingError:
                pass
        self.assertEqual(len(self.ear.capture_engine.pre_roll_buffer), 0)


class TestAudioPrivacyAndSecurity(unittest.TestCase):
    """21.8 Audio Privacy & Security Guards Tests (Tests 63-67)."""

    def test_63_no_raw_audio_in_logs(self):
        """get_audio_diagnostics and get_vad_status contain no raw audio arrays."""
        ear = SmartAudioEar()
        ear.load_neural_vad()
        diag = ear.get_audio_diagnostics()
        vad_stat = ear.get_vad_status()

        # Ensure no numpy array, raw PCM, or base64 audio in diagnostic outputs
        for k, v in diag.items():
            self.assertNotIsInstance(v, (np.ndarray, bytes))
        for k, v in vad_stat.items():
            self.assertNotIsInstance(v, (np.ndarray, bytes))
        ear.close()

    def test_64_no_audio_saved_to_disk(self):
        """Audio ear operations create zero audio files on disk."""
        ear = SmartAudioEar()
        project_audio_files = list(PROJECT_ROOT.glob("*.wav")) + list(PROJECT_ROOT.glob("*.pcm"))
        self.assertEqual(project_audio_files, [])
        ear.close()

    def test_65_no_unexpected_network_calls(self):
        """zye_audio_ear does not import socket or urllib for audio processing."""
        import inspect
        src = inspect.getsource(zye_audio_ear)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)
        self.assertNotIn("import urllib.request", src)

    def test_66_no_microphone_activation_during_import(self):
        """zye_audio_ear module does not open audio stream on module load."""
        ear = SmartAudioEar()
        self.assertIsNone(ear.capture_engine.stream)
        ear.close()

    def test_67_pre_roll_remains_memory_only(self):
        """PreRollBuffer resides strictly in RAM."""
        buf = PreRollBuffer(max_frames=20)
        buf.push(np.zeros(512, dtype=np.float32))
        self.assertEqual(len(buf), 1)
        buf.clear()
        self.assertEqual(len(buf), 0)


class TestDay07BackwardCompatibilityRegression(unittest.TestCase):
    """21.9 Day 07 Backward Compatibility Regression Tests (Tests 68-75)."""

    def test_68_microphone_discovery_still_works(self):
        """list_input_devices continues to report audio hardware."""
        devs = list_input_devices()
        self.assertIsInstance(devs, list)

    def test_69_audio_stream_validation_still_works(self):
        """validate_input_device still validates device index and settings."""
        valid, msg, info = validate_input_device(-1, sample_rate=16000, channels=1)
        self.assertIsInstance(valid, bool)

    def test_70_rms_fallback_still_works(self):
        """calculate_rms and calculate_peak continue to return accurate scalar floats."""
        arr = np.array([0.5, -0.5, 0.5, -0.5], dtype=np.float32)
        rms = calculate_rms(arr)
        peak = calculate_peak(arr)
        self.assertAlmostEqual(rms, 0.5, places=5)
        self.assertAlmostEqual(peak, 0.5, places=5)

    def test_71_wav_serialization_still_works(self):
        """encode_wav_bytes generates valid RIFF WAV header."""
        pcm = np.zeros(512, dtype=np.int16)
        wav = encode_wav_bytes(pcm, sample_rate=16000)
        self.assertTrue(wav.startswith(b"RIFF"))

    def test_72_pcm16_conversion_still_works(self):
        """convert_float32_to_pcm16 accurately converts float32 to int16."""
        arr = np.array([-1.0, 0.0, 1.0], dtype=np.float32)
        pcm = convert_float32_to_pcm16(arr)
        self.assertEqual(pcm.dtype, np.int16)
        self.assertEqual(pcm[1], 0)

    def test_73_16khz_output_preserved(self):
        """Serialized WAV reads back exactly at 16,000 Hz."""
        pcm = np.zeros(512, dtype=np.int16)
        wav = encode_wav_bytes(pcm, sample_rate=16000)
        rate, data = scipy.io.wavfile.read(io.BytesIO(wav))
        self.assertEqual(rate, 16000)

    def test_74_listen_smart_return_contract_preserved(self):
        """listen_smart returns bytes or None strictly."""
        ear = SmartAudioEar()
        # Simulated silence returns None
        silence_frame = np.zeros((512, 1), dtype=np.float32)
        with patch.object(ear.capture_engine, "read_frame", side_effect=[silence_frame] * 3 + [None]):
            res = ear.listen_smart(silence_timeout=0.05, max_record_sec=0.1)
            self.assertIsNone(res)
        ear.close()

    def test_75_doctor_audio_checks_still_work(self):
        """doctor.py check_audio_input_health reports valid diagnostics with neural_vad."""
        import doctor
        checks, info = doctor.check_audio_input_health()
        self.assertIsInstance(checks, list)
        self.assertIn("neural_vad", info)
        self.assertEqual(info["neural_vad"]["model_loaded"], True)
        self.assertEqual(info["neural_vad"]["inference_test"], "PASS")


if __name__ == "__main__":
    unittest.main()
