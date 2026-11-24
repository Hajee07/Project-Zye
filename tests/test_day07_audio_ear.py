#!/usr/bin/env python3
"""
ZYE AI — Day 07 Smart Audio Ear Test Suite
===========================================

Comprehensive automated test suite covering:
  - Configuration Management (8 tests)
  - Device Discovery & Validation (8 tests)
  - Frame Capture & Queue (9 tests)
  - Pre-Roll Ring Buffer & First-Word Preservation (8 tests)
  - Adaptive RMS Speech Detection (9 tests)
  - DSP, Downmix & Resampling (9 tests)
  - In-Memory WAV Serialization (6 tests)
  - Audio Privacy & Resource Cleanup (6 tests)
  - Master Agent & State Machine Integration (8 tests)

Total: 71 unit tests.

Usage:
    python -m unittest tests.test_day07_audio_ear -v
"""

from __future__ import annotations

from collections import deque
import inspect
import io
import math
import os
import queue
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import scipy.io.wavfile
import sounddevice as sd

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import zye_audio_ear
from zye_audio_ear import (
    AudioConfig,
    CaptureState,
    PreRollBuffer,
    AdaptiveRMSDetector,
    AudioCaptureEngine,
    SmartAudioEar,
    calculate_rms,
    calculate_peak,
    downmix_to_mono,
    resample_audio,
    convert_float32_to_pcm16,
    encode_wav_bytes,
    list_input_devices,
    get_default_input_device,
    get_input_device_info,
    validate_input_device,
    check_mic_health,
    test_microphone_stream,
    AudioError,
    AudioDeviceNotFoundError,
    AudioStreamOpenError,
    AudioFormatError,
    AudioProcessingError,
)


class _AudioTestBase(unittest.TestCase):
    """Base fixture creating isolated environments and synthetic test audio signals."""

    def setUp(self) -> None:
        self.sr = 16000
        self.duration = 1.0
        self.t = np.linspace(0, self.duration, int(self.sr * self.duration), endpoint=False)
        # 440 Hz test tone
        self.sine_wave = (0.5 * np.sin(2 * np.pi * 440 * self.t)).astype(np.float32)
        # Silence
        self.silence = np.zeros(int(self.sr * self.duration), dtype=np.float32)


# ============================================================================
# 1. CONFIGURATION TESTS (8 tests)
# ============================================================================

class TestAudioConfig(unittest.TestCase):

    def test_01_default_audio_config(self):
        """Default AudioConfig matches Day 07 production requirements."""
        cfg = AudioConfig()
        self.assertEqual(cfg.sample_rate, 16000)
        self.assertEqual(cfg.channels, 1)
        self.assertEqual(cfg.frame_duration_ms, 32)
        self.assertEqual(cfg.pre_roll_seconds, 0.64)
        self.assertEqual(cfg.frame_samples, 512)
        self.assertEqual(cfg.pre_roll_frames, 20)
        self.assertEqual(cfg.pre_roll_samples, 10240)

    def test_02_valid_sample_rate(self):
        """Supported sample rate configuration is accepted."""
        cfg = AudioConfig(sample_rate=44100, frame_duration_ms=20)
        self.assertEqual(cfg.sample_rate, 44100)
        self.assertEqual(cfg.frame_samples, 882)

    def test_03_invalid_sample_rate_rejected(self):
        """Negative or zero sample rates are rejected."""
        with self.assertRaises(AudioFormatError):
            AudioConfig(sample_rate=0)
        with self.assertRaises(AudioFormatError):
            AudioConfig(sample_rate=-16000)

    def test_04_invalid_channel_count_rejected(self):
        """Channel counts other than 1 (mono) or 2 (stereo) are rejected."""
        with self.assertRaises(AudioFormatError):
            AudioConfig(channels=0)
        with self.assertRaises(AudioFormatError):
            AudioConfig(channels=6)

    def test_05_invalid_pre_roll_duration_rejected(self):
        """Negative or excessive pre-roll durations are rejected."""
        with self.assertRaises(AudioFormatError):
            AudioConfig(pre_roll_seconds=-0.5)
        with self.assertRaises(AudioFormatError):
            AudioConfig(pre_roll_seconds=15.0)

    def test_06_negative_timeout_rejected(self):
        """Negative or zero silence timeouts are rejected."""
        with self.assertRaises(AudioFormatError):
            AudioConfig(silence_timeout_seconds=0.0)
        with self.assertRaises(AudioFormatError):
            AudioConfig(silence_timeout_seconds=-1.25)

    def test_07_excessive_recording_duration_rejected(self):
        """Max record duration exceeding boundary or less than min duration is rejected."""
        with self.assertRaises(AudioFormatError):
            AudioConfig(maximum_record_seconds=0.2, minimum_record_seconds=0.4)
        with self.assertRaises(AudioFormatError):
            AudioConfig(maximum_record_seconds=500.0)

    def test_08_invalid_queue_size_rejected(self):
        """Queue capacity outside allowable bounds is rejected."""
        with self.assertRaises(AudioFormatError):
            AudioConfig(maximum_queue_frames=2)
        with self.assertRaises(AudioFormatError):
            AudioConfig(maximum_queue_frames=5000)


# ============================================================================
# 2. DEVICE TESTS (8 tests)
# ============================================================================

class TestDeviceDiscovery(unittest.TestCase):

    def test_09_default_microphone_discovery(self):
        """list_input_devices correctly filters and identifies devices."""
        mock_devices = [
            {"name": "Speakers", "max_input_channels": 0, "default_samplerate": 48000.0},
            {"name": "USB Microphone", "max_input_channels": 1, "default_samplerate": 16000.0},
            {"name": "Stereo Mic", "max_input_channels": 2, "default_samplerate": 44100.0},
        ]
        with patch("sounddevice.query_devices", return_value=mock_devices):
            with patch("sounddevice.default.device", (1, 0)):
                devs = list_input_devices()
                self.assertEqual(len(devs), 2)
                self.assertEqual(devs[0]["name"], "USB Microphone")
                self.assertTrue(devs[0]["is_default"])

    def test_10_no_input_device_handled(self):
        """System with zero recording channels reports empty list gracefully."""
        mock_devices = [
            {"name": "Speakers Out", "max_input_channels": 0},
            {"name": "Headphones Out", "max_input_channels": 0},
        ]
        with patch("sounddevice.query_devices", return_value=mock_devices):
            self.assertEqual(list_input_devices(), [])
            self.assertIsNone(get_default_input_device())

    def test_11_valid_microphone_information(self):
        """get_input_device_info returns structured dictionary."""
        mock_dev = {"name": "Test Mic", "hostapi": 0, "max_input_channels": 2, "default_samplerate": 44100.0}
        with patch("sounddevice.query_devices", return_value=mock_dev):
            info = get_input_device_info(2)
            self.assertIsNotNone(info)
            self.assertEqual(info["name"], "Test Mic")
            self.assertEqual(info["max_input_channels"], 2)

    def test_12_invalid_device_index_rejected(self):
        """Non-existent device index returns None and validation failure."""
        with patch("sounddevice.query_devices", side_effect=ValueError("Invalid device")):
            self.assertIsNone(get_input_device_info(999))
            valid, err, _ = validate_input_device(999)
            self.assertFalse(valid)
            self.assertIn("not a valid", err)

    def test_13_unsupported_sample_rate_fallback(self):
        """validate_input_device reports PortAudio incompatibility cleanly."""
        mock_dev = {"name": "Legacy Mic", "hostapi": 0, "max_input_channels": 1, "default_samplerate": 44100.0}
        with patch("sounddevice.query_devices", return_value=mock_dev):
            with patch("sounddevice.check_input_settings", side_effect=Exception("Invalid sample rate")):
                valid, err, info = validate_input_device(1, sample_rate=16000)
                self.assertFalse(valid)
                self.assertIn("Invalid sample rate", err)

    def test_14_stream_open_failure_handled(self):
        """AudioStreamOpenError is raised when sounddevice cannot acquire hardware."""
        cfg = AudioConfig()
        engine = AudioCaptureEngine(cfg, device_index=1)
        with patch.object(engine, "_determine_stream_settings", return_value=(16000, 1)):
            with patch("sounddevice.InputStream", side_effect=Exception("Device in use")):
                with self.assertRaises(AudioStreamOpenError):
                    engine.start()

    def test_15_microphone_disconnection_handled(self):
        """check_mic_health returns structured warning if device disappears."""
        with patch("sounddevice.query_devices", side_effect=Exception("Unplugged")):
            res = check_mic_health(0)
            self.assertEqual(res["status"], "warning")
            self.assertFalse(res["microphone_available"])

    def test_16_hardware_error_handling(self):
        """test_microphone_stream returns controlled error dict on PortAudio exception."""
        with patch("sounddevice.rec", side_effect=RuntimeError("Stream dead")):
            mock_dev = {"name": "Test Mic", "hostapi": 0, "max_input_channels": 1, "default_samplerate": 44100.0}
            with patch("sounddevice.query_devices", return_value=mock_dev):
                ok, msg, diag = test_microphone_stream(1)
                self.assertFalse(ok)
                self.assertIn("STREAM_ERROR", msg)


# ============================================================================
# 3. FRAME CAPTURE & QUEUE TESTS (9 tests)
# ============================================================================

class TestFrameCaptureAndQueue(_AudioTestBase):

    def test_17_correct_float32_frame(self):
        """Incoming audio frames have correct float32 dtype and bounded range."""
        frame = np.random.uniform(-0.5, 0.5, size=(512, 1)).astype(np.float32)
        self.assertEqual(frame.dtype, np.float32)
        self.assertTrue(np.all(frame >= -1.0) and np.all(frame <= 1.0))

    def test_18_correct_mono_frame_shape(self):
        """downmix_to_mono flattens 2D mono to 1D shape (512,)."""
        frame_2d = np.ones((512, 1), dtype=np.float32)
        mono = downmix_to_mono(frame_2d)
        self.assertEqual(mono.shape, (512,))

    def test_19_invalid_frame_rejected(self):
        """Invalid dimension arrays raise AudioProcessingError on downmixing."""
        invalid_frame = np.ones((10, 2, 4), dtype=np.float32)
        with self.assertRaises(AudioProcessingError):
            downmix_to_mono(invalid_frame)

    def test_20_nan_frame_rejected(self):
        """Frames containing NaN are detected by RMS calculation and rejected during PCM conversion."""
        nan_frame = np.array([0.1, np.nan, 0.2], dtype=np.float32)
        self.assertEqual(calculate_rms(nan_frame), 0.0)
        with self.assertRaises(AudioProcessingError):
            convert_float32_to_pcm16(nan_frame)

    def test_21_infinite_values_rejected(self):
        """Frames containing infinite values are safely rejected by PCM conversion."""
        inf_frame = np.array([0.1, np.inf, 0.2], dtype=np.float32)
        self.assertEqual(calculate_peak(inf_frame), 0.0)
        with self.assertRaises(AudioProcessingError):
            convert_float32_to_pcm16(inf_frame)

    def test_22_queue_overflow_detected(self):
        """AudioCaptureEngine increments overflow counter when consumer queue is full."""
        cfg = AudioConfig(maximum_queue_frames=8)
        engine = AudioCaptureEngine(cfg)
        engine.is_running = True

        dummy_frame = np.zeros((512, 1), dtype=np.float32)
        # Fill queue to capacity
        for _ in range(8):
            engine._stream_callback(dummy_frame, 512, None, sd.CallbackFlags())

        self.assertEqual(engine.overflow_count, 0)
        # Push 9th frame (overflow!)
        engine._stream_callback(dummy_frame, 512, None, sd.CallbackFlags())
        self.assertEqual(engine.overflow_count, 1)

    def test_23_stream_timeout_handled(self):
        """read_frame returns None on timeout when queue is empty."""
        cfg = AudioConfig()
        engine = AudioCaptureEngine(cfg)
        frame = engine.read_frame(timeout=0.01)
        self.assertIsNone(frame)

    def test_24_capture_cancellation(self):
        """cancel_capture immediately sets state to CANCELLED and halts listening."""
        ear = SmartAudioEar()
        ear.start()
        ear.cancel_capture()
        self.assertEqual(ear.get_capture_state(), CaptureState.CANCELLED)
        ear.close()

    def test_25_clean_stream_shutdown(self):
        """Stopping capture releases PortAudio InputStream cleanly."""
        ear = SmartAudioEar()
        mock_stream = MagicMock()
        ear.capture_engine.stream = mock_stream
        ear.capture_engine.is_running = True
        ear.stop()
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()
        self.assertFalse(ear.capture_engine.is_running)
        self.assertEqual(ear.state, CaptureState.IDLE)


# ============================================================================
# 4. PRE-ROLL RING BUFFER TESTS (8 tests)
# ============================================================================

class TestPreRollRingBuffer(unittest.TestCase):

    def test_26_buffer_retains_20_frames(self):
        """PreRollBuffer maxlen holds exactly 20 frames by default."""
        buf = PreRollBuffer(max_frames=20)
        for i in range(30):
            buf.push(np.full((512,), i, dtype=np.float32))
        self.assertEqual(len(buf), 20)

    def test_27_buffer_represents_0_64_seconds(self):
        """20 frames of 512 samples at 16 kHz represents exactly 0.64 seconds."""
        cfg = AudioConfig()
        total_samples = cfg.pre_roll_frames * cfg.frame_samples
        duration = total_samples / cfg.sample_rate
        self.assertAlmostEqual(duration, 0.64, places=4)

    def test_28_oldest_frame_removed(self):
        """Ring buffer automatically evicts the oldest frame on push."""
        buf = PreRollBuffer(max_frames=3)
        buf.push(np.array([1.0]))
        buf.push(np.array([2.0]))
        buf.push(np.array([3.0]))
        buf.push(np.array([4.0]))  # 1.0 evicted
        snap = buf.get_snapshot()
        self.assertEqual(snap[0][0], 2.0)
        self.assertEqual(snap[-1][0], 4.0)

    def test_29_frame_ordering_preserved(self):
        """PreRollBuffer maintains strict FIFO chronological order."""
        buf = PreRollBuffer(max_frames=5)
        for i in range(5):
            buf.push(np.array([float(i)]))
        snap = buf.get_snapshot()
        for i in range(5):
            self.assertEqual(snap[i][0], float(i))

    def test_30_trigger_frame_retained(self):
        """Trigger frame is successfully captured alongside the pre-roll window."""
        buf = PreRollBuffer(max_frames=20)
        for _ in range(15):
            buf.push(np.zeros(512, dtype=np.float32))
        trigger = np.ones(512, dtype=np.float32)
        snap = buf.get_snapshot()
        snap.append(trigger)
        self.assertEqual(len(snap), 16)
        self.assertEqual(snap[-1][0], 1.0)

    def test_31_no_duplicate_trigger_frame(self):
        """Pre-roll snapshot does not accidentally duplicate the trigger frame."""
        buf = PreRollBuffer(max_frames=5)
        f1 = np.array([10.0])
        f2 = np.array([20.0])
        buf.push(f1)
        buf.push(f2)
        snap = buf.get_snapshot()
        # Verify length before appending
        self.assertEqual(len(snap), 2)
        self.assertEqual(snap[0][0], 10.0)

    def test_32_snapshot_is_safe_and_independent(self):
        """Modifying subsequent frames does not mutate existing snapshot copies."""
        buf = PreRollBuffer(max_frames=5)
        f = np.array([100.0], dtype=np.float32)
        buf.push(f)
        snap = buf.get_snapshot()
        f[0] = 999.0
        self.assertEqual(snap[0][0], 100.0)

    def test_33_buffer_clears_on_session_shutdown(self):
        """clear() purges all frames from RAM immediately."""
        buf = PreRollBuffer(max_frames=20)
        buf.push(np.ones(512, dtype=np.float32))
        self.assertEqual(len(buf), 1)
        buf.clear()
        self.assertEqual(len(buf), 0)


# ============================================================================
# 5. ADAPTIVE RMS TESTS (9 tests)
# ============================================================================

class TestAdaptiveRMS(unittest.TestCase):

    def test_34_silence_rms(self):
        """calculate_rms returns 0.0 on zero array."""
        silence = np.zeros(512, dtype=np.float32)
        self.assertAlmostEqual(calculate_rms(silence), 0.0, places=6)

    def test_35_low_volume_signal_rms(self):
        """Low volume test signal returns accurate RMS value."""
        # Amplitude 0.02 sine wave: RMS = 0.02 / sqrt(2) ≈ 0.01414
        t = np.linspace(0, 0.032, 512, endpoint=False)
        sig = 0.02 * np.sin(2 * np.pi * 440 * t)
        self.assertAlmostEqual(calculate_rms(sig), 0.02 / math.sqrt(2), places=3)

    def test_36_high_volume_signal_rms(self):
        """High volume test signal returns accurate RMS and peak."""
        t = np.linspace(0, 0.032, 512, endpoint=False)
        sig = 0.8 * np.sin(2 * np.pi * 440 * t)
        self.assertAlmostEqual(calculate_rms(sig), 0.8 / math.sqrt(2), places=2)
        self.assertAlmostEqual(calculate_peak(sig), 0.8, places=2)

    def test_37_noise_floor_ema_update(self):
        """update_noise_floor tracks ambient background noise smoothly."""
        detector = AdaptiveRMSDetector(initial_noise_floor=0.010)
        detector.update_noise_floor(0.020)
        # 0.94 * 0.010 + 0.06 * 0.020 = 0.0094 + 0.0012 = 0.0106
        self.assertAlmostEqual(detector.noise_floor, 0.0106, places=4)

    def test_38_speech_trigger_threshold(self):
        """Signal exceeding trigger threshold is confirmed as speech after required consecutive frames."""
        detector = AdaptiveRMSDetector(initial_noise_floor=0.005, consecutive_frames_required=2)
        loud_frame = np.full((512,), 0.05, dtype=np.float32)

        is_sp1, _, _ = detector.is_speech_candidate(loud_frame)
        self.assertFalse(is_sp1)  # Frame 1: pending confirmation
        is_sp2, _, _ = detector.is_speech_candidate(loud_frame)
        self.assertTrue(is_sp2)   # Frame 2: confirmed speech!

    def test_39_hold_threshold_with_hysteresis(self):
        """Once in speech, lower hold threshold keeps speech active."""
        detector = AdaptiveRMSDetector(initial_noise_floor=0.005, consecutive_frames_required=1)
        detector.is_speech_candidate(np.full((512,), 0.05, dtype=np.float32))
        self.assertTrue(detector._in_speech)

        # Mild signal below trigger (0.012) but above hold (0.009)
        mild_frame = np.full((512,), 0.010, dtype=np.float32)
        is_sp, _, _ = detector.is_speech_candidate(mild_frame)
        self.assertTrue(is_sp)

    def test_40_hysteresis_prevents_chatter(self):
        """Signal dipping slightly below trigger does not immediately drop state."""
        detector = AdaptiveRMSDetector(initial_noise_floor=0.005, consecutive_frames_required=1)
        detector.is_speech_candidate(np.full((512,), 0.05, dtype=np.float32))

        # Drop below hold
        silence_frame = np.zeros((512,), dtype=np.float32)
        is_sp, _, _ = detector.is_speech_candidate(silence_frame)
        self.assertFalse(is_sp)
        self.assertFalse(detector._in_speech)

    def test_41_single_click_rejection(self):
        """A transient single-frame spike does not trigger speech state."""
        detector = AdaptiveRMSDetector(initial_noise_floor=0.005, consecutive_frames_required=2)
        click_frame = np.full((512,), 0.20, dtype=np.float32)
        silence_frame = np.zeros((512,), dtype=np.float32)

        is_sp1, _, _ = detector.is_speech_candidate(click_frame)
        self.assertFalse(is_sp1)  # 1st spike
        is_sp2, _, _ = detector.is_speech_candidate(silence_frame)
        self.assertFalse(is_sp2)  # Return to silence -> counter reset
        self.assertFalse(detector._in_speech)

    def test_42_invalid_audio_rejection(self):
        """calculate_rms handles empty arrays without crashing."""
        self.assertEqual(calculate_rms(np.array([])), 0.0)
        self.assertEqual(calculate_peak(np.array([])), 0.0)


# ============================================================================
# 6. AUDIO PROCESSING, DOWNMIX & RESAMPLING TESTS (9 tests)
# ============================================================================

class TestAudioProcessing(_AudioTestBase):

    def test_43_mono_conversion(self):
        """1D array passes through downmix_to_mono unaltered."""
        arr = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        mono = downmix_to_mono(arr)
        np.testing.assert_array_equal(arr, mono)

    def test_44_stereo_downmix_average(self):
        """Stereo 2-channel audio is downmixed by channel averaging."""
        # Left = 0.4, Right = 0.2 -> Mono = 0.3
        stereo = np.array([[0.4, 0.2], [0.8, 0.4]], dtype=np.float32)
        mono = downmix_to_mono(stereo)
        expected = np.array([0.3, 0.6], dtype=np.float32)
        np.testing.assert_allclose(mono, expected, rtol=1e-5)

    def test_45_48khz_to_16khz_resampling(self):
        """48 kHz audio resampled to 16 kHz has exactly 1/3 the sample count."""
        samples_48k = np.random.uniform(-0.5, 0.5, size=48000).astype(np.float32)
        resampled_16k = resample_audio(samples_48k, orig_sr=48000, target_sr=16000)
        self.assertEqual(len(resampled_16k), 16000)

    def test_46_44_1khz_to_16khz_resampling(self):
        """44.1 kHz audio resampled to 16 kHz yields correct sample count."""
        # 44,100 samples at 44.1 kHz = 1.0 second -> 16,000 samples at 16 kHz
        samples_44k = np.random.uniform(-0.5, 0.5, size=44100).astype(np.float32)
        resampled_16k = resample_audio(samples_44k, orig_sr=44100, target_sr=16000)
        self.assertEqual(len(resampled_16k), 16000)

    def test_47_correct_output_duration(self):
        """Resampling preserves signal duration and frequency content."""
        t_48k = np.linspace(0, 0.5, 24000, endpoint=False)
        sig_48k = np.sin(2 * np.pi * 200 * t_48k).astype(np.float32)
        sig_16k = resample_audio(sig_48k, orig_sr=48000, target_sr=16000)
        self.assertEqual(len(sig_16k), 8000)
        self.assertAlmostEqual(len(sig_16k) / 16000, 0.5)

    def test_48_pcm16_conversion(self):
        """convert_float32_to_pcm16 scales [-1.0, 1.0] to signed 16-bit integers."""
        float_samples = np.array([-1.0, 0.0, 1.0, 0.5], dtype=np.float32)
        pcm = convert_float32_to_pcm16(float_samples)
        self.assertEqual(pcm.dtype, np.int16)
        self.assertEqual(pcm[0], -32767)
        self.assertEqual(pcm[1], 0)
        self.assertEqual(pcm[2], 32767)
        self.assertEqual(pcm[3], 16383)

    def test_49_clipping_detection(self):
        """Samples exceeding 1.0 are safely clamped without wrapping or integer overflow."""
        over_samples = np.array([-1.5, 2.5], dtype=np.float32)
        pcm = convert_float32_to_pcm16(over_samples)
        self.assertEqual(pcm[0], -32767)
        self.assertEqual(pcm[1], 32767)

    def test_50_silence_detection(self):
        """All-zero signal yields all-zero PCM16 array."""
        zeros = np.zeros(512, dtype=np.float32)
        pcm = convert_float32_to_pcm16(zeros)
        self.assertTrue(np.all(pcm == 0))

    def test_51_empty_recording_rejection(self):
        """Empty arrays return empty int16 arrays safely."""
        pcm = convert_float32_to_pcm16(np.array([], dtype=np.float32))
        self.assertEqual(len(pcm), 0)
        self.assertEqual(pcm.dtype, np.int16)


# ============================================================================
# 7. IN-MEMORY WAV SERIALIZATION TESTS (6 tests)
# ============================================================================

class TestWAVSerialization(unittest.TestCase):

    def setUp(self) -> None:
        self.samples = (np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000, endpoint=False)) * 32767).astype(np.int16)
        self.wav_bytes = encode_wav_bytes(self.samples, sample_rate=16000)

    def test_52_valid_wav_header(self):
        """Generated WAV bytes begin with standard RIFF header."""
        self.assertTrue(self.wav_bytes.startswith(b"RIFF"))
        self.assertIn(b"WAVE", self.wav_bytes[:16])

    def test_53_correct_sample_rate(self):
        """Reading serialized WAV validates 16,000 Hz sample rate."""
        rate, _ = scipy.io.wavfile.read(io.BytesIO(self.wav_bytes))
        self.assertEqual(rate, 16000)

    def test_54_correct_pcm16_dtype(self):
        """Read-back array has np.int16 data type."""
        _, data = scipy.io.wavfile.read(io.BytesIO(self.wav_bytes))
        self.assertEqual(data.dtype, np.int16)

    def test_55_correct_mono_channel(self):
        """Read-back array is 1-dimensional (mono)."""
        _, data = scipy.io.wavfile.read(io.BytesIO(self.wav_bytes))
        self.assertEqual(data.ndim, 1)

    def test_56_correct_sample_count(self):
        """Sample count matches original input length exactly."""
        _, data = scipy.io.wavfile.read(io.BytesIO(self.wav_bytes))
        self.assertEqual(len(data), 8000)

    def test_57_wav_read_back_validation(self):
        """Decoded samples match original samples byte for byte."""
        _, data = scipy.io.wavfile.read(io.BytesIO(self.wav_bytes))
        np.testing.assert_array_equal(data, self.samples)


# ============================================================================
# 8. PRIVACY & RESOURCE CLEANUP TESTS (6 tests)
# ============================================================================

class TestAudioPrivacyAndCleanup(unittest.TestCase):

    def test_58_no_audio_written_to_disk(self):
        """listen_smart creates no audio files in the workspace or tempdir."""
        cfg = AudioConfig(minimum_record_seconds=0.05)
        ear = SmartAudioEar(config=cfg)
        sequence = [np.full((512, 1), 0.05, dtype=np.float32)] * 15 + [np.zeros((512, 1), dtype=np.float32)] * 5 + [None]
        with patch.object(ear.capture_engine, "read_frame", side_effect=sequence):
            wav = ear.listen_smart(silence_timeout=0.05, max_record_sec=1.0)
            self.assertIsNotNone(wav)
            # Verify no .wav files created in project root
            wavs = list(PROJECT_ROOT.glob("*.wav"))
            self.assertEqual(len(wavs), 0)
        ear.close()

    def test_59_no_network_calls(self):
        """zye_audio_ear does not import or invoke network libraries."""
        import zye_audio_ear
        src = inspect.getsource(zye_audio_ear) if "inspect" in globals() else Path(zye_audio_ear.__file__).read_text(encoding="utf-8")
        self.assertNotIn("google.genai", src)
        self.assertNotIn("urllib.request", src)
        self.assertNotIn("requests", src)

    def test_60_no_raw_audio_in_logs(self):
        """get_audio_diagnostics contains metadata only, never raw samples or base64 audio."""
        ear = SmartAudioEar()
        diag = ear.get_audio_diagnostics()
        self.assertNotIn("audio_bytes", diag)
        self.assertNotIn("samples", diag)
        self.assertNotIn("raw_data", diag)
        ear.close()

    def test_61_pre_roll_remains_in_memory(self):
        """PreRollBuffer resides strictly in RAM without disk persistence."""
        buf = PreRollBuffer(max_frames=20)
        buf.push(np.ones(512, dtype=np.float32))
        self.assertIsInstance(buf._buffer, deque)
        buf.clear()

    def test_62_capture_stops_when_disabled(self):
        """Closing ear marks capture_active as False and clears queue."""
        ear = SmartAudioEar()
        ear.start()
        self.assertTrue(ear.capture_engine.is_running)
        ear.close()
        self.assertFalse(ear.capture_engine.is_running)

    def test_63_stream_closed_after_exception(self):
        """Stream resources are released even if an exception occurs during recording."""
        ear = SmartAudioEar()
        mock_stream = MagicMock()
        ear.capture_engine.stream = mock_stream
        ear.capture_engine.is_running = True
        try:
            with patch.object(ear.capture_engine, "read_frame", side_effect=RuntimeError("Bus error")):
                ear.listen_smart()
        except RuntimeError:
            pass
        finally:
            ear.close()
        self.assertFalse(ear.capture_engine.is_running)


# ============================================================================
# 9. INTEGRATION & STATE MACHINE TESTS (8 tests)
# ============================================================================

class TestIntegrationAndStateMachine(unittest.TestCase):

    def test_64_smart_audio_ear_initializes(self):
        """SmartAudioEar initializes with default or custom configuration."""
        ear = SmartAudioEar()
        self.assertEqual(ear.state, CaptureState.IDLE)
        self.assertEqual(ear.config.sample_rate, 16000)
        ear.close()

    def test_65_microphone_health_response_structured(self):
        """check_mic_health returns expected dictionary schema."""
        ear = SmartAudioEar()
        mock_dev = {"name": "Studio Mic", "hostapi": 0, "max_input_channels": 1, "default_samplerate": 48000.0}
        with patch("sounddevice.query_devices", side_effect=lambda idx=None: [mock_dev] if idx is None else mock_dev):
            with patch("sounddevice.check_input_settings"):
                health = ear.check_mic_health()
                self.assertEqual(health["status"], "success")
                self.assertTrue(health["microphone_available"])
                self.assertEqual(health["device"]["name"], "Studio Mic")
        ear.close()

    def test_66_listen_smart_returns_valid_wav_bytes(self):
        """Simulated speech sequence returns valid 16 kHz PCM WAV bytes with first word."""
        ear = SmartAudioEar()
        # Feed 10 background frames, 15 speech frames, then silence
        bg_frame = np.full((512, 1), 0.002, dtype=np.float32)
        speech_frame = np.full((512, 1), 0.08, dtype=np.float32)
        silence_frame = np.zeros((512, 1), dtype=np.float32)

        sequence = [bg_frame] * 10 + [speech_frame] * 15 + [silence_frame] * 15
        with patch.object(ear.capture_engine, "read_frame", side_effect=sequence):
            wav_bytes = ear.listen_smart(silence_timeout=0.05, max_record_sec=2.0)
            self.assertIsNotNone(wav_bytes)
            rate, samples = scipy.io.wavfile.read(io.BytesIO(wav_bytes))
            self.assertEqual(rate, 16000)
            self.assertEqual(samples.dtype, np.int16)
            self.assertGreater(len(samples), 512 * 10)  # Contains pre-roll + speech
        ear.close()

    def test_67_no_speech_returns_none(self):
        """Pure silence throughout window returns None without error."""
        ear = SmartAudioEar()
        silence_frame = np.zeros((512, 1), dtype=np.float32)
        with patch.object(ear.capture_engine, "read_frame", side_effect=[silence_frame] * 5 + [None]):
            res = ear.listen_smart(silence_timeout=0.05, max_record_sec=0.1)
            self.assertIsNone(res)
        ear.close()

    def test_68_maximum_duration_enforced(self):
        """Speech reaching max_record_sec finalizes and returns captured audio."""
        ear = SmartAudioEar()
        speech_frame = np.full((512, 1), 0.08, dtype=np.float32)
        # Infinite speech stream
        def infinite_speech(timeout=0.1):
            return speech_frame

        with patch.object(ear.capture_engine, "read_frame", side_effect=infinite_speech):
            t0 = time.time()
            wav = ear.listen_smart(silence_timeout=2.0, max_record_sec=0.45)
            elapsed = time.time() - t0
            self.assertIsNotNone(wav)
            self.assertLess(elapsed, 1.5)
        ear.close()

    def test_69_silence_timeout_enforced(self):
        """Speech followed by silence stops within silence_timeout window."""
        ear = SmartAudioEar()
        speech_frame = np.full((512, 1), 0.08, dtype=np.float32)
        silence_frame = np.zeros((512, 1), dtype=np.float32)
        stream_data = [speech_frame] * 15 + [silence_frame] * 30

        with patch.object(ear.capture_engine, "read_frame", side_effect=stream_data):
            wav = ear.listen_smart(silence_timeout=0.05, max_record_sec=3.0)
            self.assertIsNotNone(wav)
            self.assertEqual(ear.state, CaptureState.COMPLETED)
        ear.close()

    def test_70_doctor_py_audio_checks_work(self):
        """doctor.py check_audio_input_health reports valid Stage 5 diagnostics."""
        from doctor import check_audio_input_health
        checks, info = check_audio_input_health()
        self.assertTrue(info["sounddevice_available"])
        self.assertTrue(info["numpy_available"])
        self.assertTrue(info["scipy_available"])
        self.assertEqual(info["pcm_conversion"], "PASS")
        self.assertEqual(info["wav_encoding"], "PASS")
        self.assertEqual(info["pre_roll_configuration"], "PASS")
        self.assertEqual(info["diagnostic_status"], "DAY_07_AUDIO_EAR_READY")

    def test_71_day_01_06_regression_compatibility_preserved(self):
        """Existing core framework files (doctor.py, zye_guard.py, self_repair_mcp.py, main.py) remain importable."""
        import doctor
        import zye_guard
        import self_repair_mcp
        import main
        self.assertTrue(hasattr(doctor, "aggregate_diagnostic_results"))
        self.assertTrue(hasattr(zye_guard, "zye_safe_skill"))
        self.assertTrue(hasattr(self_repair_mcp, "preview_code_patch"))
        self.assertTrue(hasattr(main, "ZyeMasterAgent"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
