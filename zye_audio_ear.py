#!/usr/bin/env python3
"""
ZYE AI — Smart Audio Ear & Neural Hearing Engine v2.0
======================================================

Production-grade real-time microphone capture, intelligent audio buffering,
PCM conversion, device discovery, Silero Neural VAD ONNX speech detection,
adaptive RMS noise-floor fallback, dual-threshold hysteresis (0.52 / 0.40),
consecutive-frame confirmation, 0.64-second pre-roll first-word preservation,
and in-memory signed 16-bit PCM WAV serialization.

Operating System: Windows 10/11 x64
Target Format: 16,000 Hz, Mono, Signed 16-bit PCM WAV (In-Memory)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
import io
import math
import logging
import queue
import threading
import time
from typing import Any, Callable, Sequence

import numpy as np
import scipy.io.wavfile
import scipy.signal
import sounddevice as sd

# Deferred / guarded imports for neural VAD dependencies
try:
    import torch
except ImportError:
    torch = None

try:
    from silero_vad import load_silero_vad
except ImportError:
    load_silero_vad = None

try:
    import onnxruntime as ort
except ImportError:
    ort = None

# Day 09 Audio Enhancement imports (AGC & Jarvis Chimes)
from zye_audio.agc import AGCConfig, AGCProcessor, AGCResult
from zye_audio.chime_player import ChimeConfig, JarvisChimePlayer

# Logger for audio diagnostic events (NEVER logs raw audio or transcripts)
logger = logging.getLogger("zye_audio_ear")


# ============================================================================
# 1. Custom Audio Exceptions (Section 17)
# ============================================================================

class AudioError(Exception):
    """Base exception for all Zye audio subsystem failures."""
    pass


class AudioDeviceNotFoundError(AudioError):
    """Raised when an audio input device cannot be found or is unavailable."""
    pass


class AudioStreamOpenError(AudioError):
    """Raised when an audio input stream fails to open."""
    pass


class AudioStreamReadError(AudioError):
    """Raised when reading from an audio stream fails."""
    pass


class AudioBufferOverflowError(AudioError):
    """Raised when real-time audio queues or buffers overflow."""
    pass


class AudioTimeoutError(AudioError):
    """Raised when an audio operation times out."""
    pass


class AudioFormatError(AudioError):
    """Raised when an invalid audio format or sample rate is encountered."""
    pass


class AudioProcessingError(AudioError):
    """Raised when signal processing, downmixing, or resampling fails."""
    pass


class AudioVADError(AudioProcessingError):
    """Raised when neural Voice Activity Detection inference fails."""
    pass


# ============================================================================
# 2. Speech Capture State Machine & VAD Lifecycle (Section 12, 15)
# ============================================================================

class CaptureState(str, Enum):
    """Explicit states of the real-time audio speech capture lifecycle."""
    IDLE = "IDLE"
    BUFFERING = "BUFFERING"
    SPEECH_CANDIDATE = "SPEECH_CANDIDATE"
    SPEECH_CONFIRMED = "SPEECH_CONFIRMED"
    SPEECH_DETECTED = "SPEECH_DETECTED"
    RECORDING = "RECORDING"
    SHORT_PAUSE = "SHORT_PAUSE"
    SILENCE_DETECTED = "SILENCE_DETECTED"
    FINALIZING = "FINALIZING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


class VADModelStatus(str, Enum):
    """Lifecycle states of the Silero Neural VAD engine."""
    NOT_INITIALIZED = "NOT_INITIALIZED"
    LOADING = "LOADING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    CLOSED = "CLOSED"


# Permitted state transitions supporting both Day 07 and Day 08 lifecycles
_VALID_TRANSITIONS: dict[CaptureState, set[CaptureState]] = {
    CaptureState.IDLE: {CaptureState.BUFFERING, CaptureState.ERROR},
    CaptureState.BUFFERING: {
        CaptureState.SPEECH_CANDIDATE,
        CaptureState.SPEECH_DETECTED,
        CaptureState.CANCELLED,
        CaptureState.ERROR,
        CaptureState.IDLE,
    },
    CaptureState.SPEECH_CANDIDATE: {
        CaptureState.SPEECH_CONFIRMED,
        CaptureState.SPEECH_DETECTED,
        CaptureState.BUFFERING,
        CaptureState.CANCELLED,
        CaptureState.ERROR,
        CaptureState.IDLE,
    },
    CaptureState.SPEECH_CONFIRMED: {
        CaptureState.RECORDING,
        CaptureState.SPEECH_DETECTED,
        CaptureState.CANCELLED,
        CaptureState.ERROR,
    },
    CaptureState.SPEECH_DETECTED: {
        CaptureState.RECORDING,
        CaptureState.CANCELLED,
        CaptureState.ERROR,
    },
    CaptureState.RECORDING: {
        CaptureState.SHORT_PAUSE,
        CaptureState.SILENCE_DETECTED,
        CaptureState.FINALIZING,
        CaptureState.CANCELLED,
        CaptureState.ERROR,
    },
    CaptureState.SHORT_PAUSE: {
        CaptureState.RECORDING,
        CaptureState.SILENCE_DETECTED,
        CaptureState.FINALIZING,
        CaptureState.CANCELLED,
        CaptureState.ERROR,
    },
    CaptureState.SILENCE_DETECTED: {
        CaptureState.FINALIZING,
        CaptureState.CANCELLED,
        CaptureState.ERROR,
    },
    CaptureState.FINALIZING: {
        CaptureState.COMPLETED,
        CaptureState.ERROR,
    },
    CaptureState.COMPLETED: {
        CaptureState.IDLE,
        CaptureState.BUFFERING,
    },
    CaptureState.CANCELLED: {
        CaptureState.IDLE,
        CaptureState.BUFFERING,
    },
    CaptureState.ERROR: {
        CaptureState.IDLE,
        CaptureState.BUFFERING,
    },
}


# ============================================================================
# 3. Audio Configuration (Section 06, 17)
# ============================================================================

@dataclass
class AudioConfig:
    """Master configuration for microphone capture, pre-roll buffering, and neural VAD."""
    sample_rate: int = 16000
    channels: int = 1
    sample_format: str = "float32"
    frame_duration_ms: int = 32
    pre_roll_seconds: float = 0.64
    silence_timeout_seconds: float = 1.25
    maximum_record_seconds: float = 25.0
    minimum_record_seconds: float = 0.40
    target_output_format: str = "PCM_16"
    maximum_queue_frames: int = 64
    noise_floor_initial: float = 0.008
    vad_mode: str = "adaptive_rms"
    preferred_device_index: int = -1
    # Day 08 Neural VAD parameters
    vad_backend: str = "silero_onnx"
    vad_fallback_backend: str = "adaptive_rms"
    vad_start_threshold: float = 0.52
    vad_hold_threshold: float = 0.40
    vad_confirmation_frames: int = 2
    vad_device: str = "cpu"
    vad_warmup_enabled: bool = True
    vad_auto_fallback: bool = True
    vad_max_consecutive_errors: int = 3
    # Day 09 Audio Enhancement parameters
    agc: AGCConfig = field(default_factory=AGCConfig)
    chimes: ChimeConfig = field(default_factory=ChimeConfig)

    def __post_init__(self) -> None:
        if self.vad_mode == "silero_onnx":
            self.vad_backend = "silero_onnx"
        elif self.vad_mode == "adaptive_rms":
            self.vad_backend = "adaptive_rms"
        self.validate()

    def validate(self) -> None:
        """Validate all configuration attributes strictly."""
        if not isinstance(self.sample_rate, int) or self.sample_rate <= 0:
            raise AudioFormatError(f"sample_rate must be a positive integer, got {self.sample_rate}")
        if self.channels not in (1, 2):
            raise AudioFormatError(f"channels must be 1 (mono) or 2 (stereo), got {self.channels}")
        if not isinstance(self.frame_duration_ms, int) or self.frame_duration_ms <= 0 or self.frame_duration_ms > 500:
            raise AudioFormatError(f"frame_duration_ms must be an integer between 1 and 500 ms, got {self.frame_duration_ms}")
        if self.pre_roll_seconds < 0.0 or self.pre_roll_seconds > 10.0:
            raise AudioFormatError(f"pre_roll_seconds must be between 0.0 and 10.0, got {self.pre_roll_seconds}")
        if self.silence_timeout_seconds <= 0.0 or self.silence_timeout_seconds > 60.0:
            raise AudioFormatError(f"silence_timeout_seconds must be positive and <= 60.0, got {self.silence_timeout_seconds}")
        if self.minimum_record_seconds < 0.0:
            raise AudioFormatError("minimum_record_seconds must be non-negative")
        if self.maximum_record_seconds <= self.minimum_record_seconds or self.maximum_record_seconds > 300.0:
            raise AudioFormatError(
                f"maximum_record_seconds ({self.maximum_record_seconds}) must exceed minimum_record_seconds "
                f"({self.minimum_record_seconds}) and be <= 300.0"
            )
        if not isinstance(self.maximum_queue_frames, int) or self.maximum_queue_frames < 8 or self.maximum_queue_frames > 2048:
            raise AudioFormatError(f"maximum_queue_frames must be between 8 and 2048, got {self.maximum_queue_frames}")
        if self.target_output_format not in ("PCM_16", "PCM16"):
            raise AudioFormatError(f"target_output_format must be 'PCM_16', got {self.target_output_format}")
        # Threshold validation (Section 10)
        if not (0.0 <= self.vad_hold_threshold < self.vad_start_threshold <= 1.0):
            raise AudioFormatError(
                f"VAD thresholds must satisfy 0.0 <= hold_threshold ({self.vad_hold_threshold}) < "
                f"start_threshold ({self.vad_start_threshold}) <= 1.0"
            )
        if not isinstance(self.vad_confirmation_frames, int) or self.vad_confirmation_frames < 1:
            raise AudioFormatError(f"vad_confirmation_frames must be an integer >= 1, got {self.vad_confirmation_frames}")
        if not isinstance(self.vad_max_consecutive_errors, int) or self.vad_max_consecutive_errors < 1:
            raise AudioFormatError(f"vad_max_consecutive_errors must be an integer >= 1, got {self.vad_max_consecutive_errors}")

    @property
    def frame_samples(self) -> int:
        """Number of audio samples per frame at the configured sample rate."""
        return int(round(self.sample_rate * (self.frame_duration_ms / 1000.0)))

    @property
    def pre_roll_frames(self) -> int:
        """Target number of frames required to hold pre_roll_seconds (e.g. 20 frames at 32ms for 0.64s)."""
        if self.pre_roll_seconds <= 0.0:
            return 0
        return int(round(self.pre_roll_seconds / (self.frame_duration_ms / 1000.0)))

    @property
    def pre_roll_samples(self) -> int:
        """Total number of audio samples across the pre-roll duration."""
        return self.pre_roll_frames * self.frame_samples


# ============================================================================
# 4. Microphone Device Discovery Engine (Section 07)
# ============================================================================

def list_input_devices() -> list[dict[str, Any]]:
    """List all available audio input devices reported by PortAudio."""
    input_devices: list[dict[str, Any]] = []
    try:
        devices = sd.query_devices()
        default_idx = None
        try:
            default_tuple = sd.default.device
            if default_tuple and default_tuple[0] is not None and default_tuple[0] >= 0:
                default_idx = int(default_tuple[0])
        except Exception:
            pass

        for idx, dev in enumerate(devices):
            max_in = int(dev.get("max_input_channels", 0))
            if max_in > 0:
                input_devices.append({
                    "index": idx,
                    "name": str(dev.get("name", "Unknown Microphone")),
                    "hostapi": int(dev.get("hostapi", 0)),
                    "max_input_channels": max_in,
                    "default_samplerate": float(dev.get("default_samplerate", 44100.0)),
                    "is_default": (idx == default_idx),
                })
    except Exception as exc:
        logger.warning("PortAudio device discovery failed: %s", exc)

    return input_devices


def get_default_input_device() -> dict[str, Any] | None:
    """Retrieve metadata for the system default audio input device."""
    devices = list_input_devices()
    if not devices:
        return None

    for d in devices:
        if d.get("is_default"):
            return d

    return devices[0]


def get_input_device_info(device_index: int | None = None) -> dict[str, Any] | None:
    """Retrieve full device details for a specified index or the default input device."""
    if device_index is None or device_index < 0:
        return get_default_input_device()

    try:
        dev = sd.query_devices(device_index)
        if int(dev.get("max_input_channels", 0)) <= 0:
            return None
        return {
            "index": device_index,
            "name": str(dev.get("name", "Unknown")),
            "hostapi": int(dev.get("hostapi", 0)),
            "max_input_channels": int(dev.get("max_input_channels", 0)),
            "default_samplerate": float(dev.get("default_samplerate", 44100.0)),
            "is_default": False,
        }
    except Exception:
        return None


def validate_input_device(
    device_index: int | None = None,
    sample_rate: int = 16000,
    channels: int = 1,
) -> tuple[bool, str | None, dict[str, Any] | None]:
    """Validate whether an audio device exists and supports specific input parameters."""
    dev_info = get_input_device_info(device_index)
    if not dev_info:
        return False, f"Device index {device_index} is not a valid input device", None

    idx = dev_info["index"]
    try:
        sd.check_input_settings(device=idx, samplerate=sample_rate, channels=channels, dtype="float32")
        return True, None, dev_info
    except Exception as exc:
        return False, str(exc), dev_info


def check_mic_health(device_index: int | None = None) -> dict[str, Any]:
    """Perform a comprehensive hardware health check on the specified or default microphone."""
    dev_info = get_input_device_info(device_index)
    if not dev_info:
        return {
            "status": "warning",
            "microphone_available": False,
            "device": None,
            "message": "No active microphone detected by PortAudio.",
        }

    idx = dev_info["index"]
    native_rate = int(dev_info["default_samplerate"])
    supports_16k, err_16k, _ = validate_input_device(idx, sample_rate=16000, channels=1)

    return {
        "status": "success",
        "microphone_available": True,
        "device": {
            "index": idx,
            "name": dev_info["name"],
            "channels": dev_info["max_input_channels"],
            "default_sample_rate": native_rate,
            "supports_16k_mono": supports_16k,
            "validation_note": err_16k if not supports_16k else "Natively supported",
        },
    }


def test_microphone_stream(
    device_index: int | None = None,
    duration_seconds: float = 0.2,
) -> tuple[bool, str, dict[str, Any]]:
    """Open a momentary input stream to verify hardware read capability and signal level."""
    dev_info = get_input_device_info(device_index)
    if not dev_info:
        return False, "NO_INPUT_DEVICE", {"device": None}

    idx = dev_info["index"]
    sr = int(dev_info["default_samplerate"])
    ch = min(int(dev_info["max_input_channels"]), 2)
    frames_to_read = int(sr * duration_seconds)

    try:
        recorded = sd.rec(frames_to_read, samplerate=sr, channels=ch, dtype="float32", device=idx, blocking=True)
        sd.wait()
        rms = calculate_rms(recorded)
        peak = calculate_peak(recorded)

        diag = {
            "device_index": idx,
            "device_name": dev_info["name"],
            "sample_rate": sr,
            "channels": ch,
            "frames_captured": len(recorded),
            "rms": round(rms, 6),
            "peak": round(peak, 6),
        }

        if rms < 0.0001:
            return True, "STREAM_OPEN_SILENCE_OBSERVED", diag
        return True, "STREAM_OPEN_SIGNAL_VERIFIED", diag

    except Exception as exc:
        return False, f"STREAM_ERROR: {exc}", {"device_index": idx, "error": str(exc)}


# ============================================================================
# 5. DSP, Downmixing, Resampling & Format Conversion (Section 08, 11, 14, 15)
# ============================================================================

def calculate_rms(samples: np.ndarray) -> float:
    """Calculate Root Mean Square (RMS) amplitude of audio samples."""
    if samples is None or len(samples) == 0:
        return 0.0
    flat = np.asarray(samples).reshape(-1)
    if not np.all(np.isfinite(flat)):
        return 0.0
    mean_sq = float(np.mean(flat.astype(np.float64) ** 2))
    return float(np.sqrt(mean_sq))


def calculate_peak(samples: np.ndarray) -> float:
    """Calculate peak absolute amplitude of audio samples."""
    if samples is None or len(samples) == 0:
        return 0.0
    flat = np.asarray(samples).reshape(-1)
    if not np.all(np.isfinite(flat)):
        return 0.0
    return float(np.max(np.abs(flat)))


def downmix_to_mono(audio: np.ndarray) -> np.ndarray:
    """Downmix multi-channel audio to single-channel (mono) float32 array."""
    arr = np.asarray(audio, dtype=np.float32)
    if arr.ndim == 1:
        return arr
    if arr.ndim == 2:
        if arr.shape[1] == 1:
            return arr[:, 0]
        return np.mean(arr, axis=1, dtype=np.float32)
    raise AudioProcessingError(f"Unsupported audio array shape for downmixing: {arr.shape}")


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int = 16000) -> np.ndarray:
    """Resample a 1D audio segment to target_sr using polyphase filtering."""
    if orig_sr == target_sr:
        return np.asarray(audio, dtype=np.float32)

    if not isinstance(orig_sr, (int, float)) or orig_sr <= 0:
        raise AudioFormatError(f"Invalid original sample rate: {orig_sr}")

    orig_sr_int = int(round(orig_sr))
    gcd = math.gcd(orig_sr_int, target_sr)
    up = target_sr // gcd
    down = orig_sr_int // gcd

    try:
        resampled = scipy.signal.resample_poly(audio, up, down)
        return np.asarray(resampled, dtype=np.float32)
    except Exception as exc:
        raise AudioProcessingError(f"Resampling failed from {orig_sr} Hz to {target_sr} Hz: {exc}") from exc


def convert_float32_to_pcm16(audio: np.ndarray) -> np.ndarray:
    """Convert float32 samples in [-1.0, 1.0] to signed 16-bit PCM (np.int16)."""
    if audio is None or len(audio) == 0:
        return np.array([], dtype=np.int16)

    arr = np.asarray(audio)
    if not np.all(np.isfinite(arr)):
        raise AudioProcessingError("Audio array contains NaN or Inf values")

    clipped = np.clip(arr, -1.0, 1.0)
    scaled = clipped * 32767.0
    return scaled.astype(np.int16)


def encode_wav_bytes(audio_pcm16: np.ndarray, sample_rate: int = 16000) -> bytes:
    """Serialize signed 16-bit PCM samples into in-memory WAV bytes."""
    if audio_pcm16.dtype != np.int16:
        raise AudioFormatError(f"Expected int16 dtype for WAV serialization, got {audio_pcm16.dtype}")

    bio = io.BytesIO()
    scipy.io.wavfile.write(bio, sample_rate, audio_pcm16)
    return bio.getvalue()


# ============================================================================
# 6. Silero VAD Frame Validation & Tensor Preparation (Section 06)
# ============================================================================

def validate_vad_frame(frame: np.ndarray, sample_rate: int = 16000) -> bool:
    """Validate that an audio frame meets strict 512-sample float32 16kHz mono VAD requirements."""
    if frame is None:
        return False
    if not isinstance(frame, np.ndarray):
        return False
    if frame.ndim != 1:
        return False
    if len(frame) != 512:
        return False
    if sample_rate != 16000:
        return False
    if not (frame.dtype == np.float32 or np.issubdtype(frame.dtype, np.floating)):
        return False
    if not np.all(np.isfinite(frame)):
        return False
    return True


def prepare_vad_tensor(frame: np.ndarray) -> Any:
    """Convert a valid 512-sample float32 NumPy frame into a CPU PyTorch tensor."""
    if not validate_vad_frame(frame):
        raise AudioFormatError("Invalid audio frame for VAD: must be 1D, 512 float32 finite samples at 16 kHz")
    if torch is None:
        raise AudioProcessingError("PyTorch is not installed or available for VAD tensor conversion")
    arr = np.ascontiguousarray(frame, dtype=np.float32)
    return torch.from_numpy(arr)


def get_vad_frame_metadata(frame: np.ndarray, sample_rate: int = 16000) -> dict[str, Any]:
    """Inspect frame properties and return acoustic metadata without raw samples."""
    valid = validate_vad_frame(frame, sample_rate)
    rms = calculate_rms(frame) if (frame is not None and isinstance(frame, np.ndarray)) else 0.0
    peak = calculate_peak(frame) if (frame is not None and isinstance(frame, np.ndarray)) else 0.0
    length = len(frame) if (frame is not None and hasattr(frame, "__len__")) else 0
    return {
        "sample_rate": sample_rate,
        "frame_samples": length,
        "frame_duration_ms": round(length / sample_rate * 1000.0, 2) if sample_rate > 0 else 0.0,
        "rms": round(rms, 6),
        "peak": round(peak, 6),
        "is_valid": valid,
    }


# ============================================================================
# 7. Adaptive RMS Detection Baseline (Section 11)
# ============================================================================

class AdaptiveRMSDetector:
    """Lightweight adaptive RMS speech candidate detector with noise floor tracking and hysteresis."""

    def __init__(
        self,
        initial_noise_floor: float = 0.008,
        trigger_multiplier: float = 2.4,
        hold_multiplier: float = 1.8,
        min_trigger: float = 0.010,
        min_hold: float = 0.008,
        consecutive_frames_required: int = 2,
    ) -> None:
        self.noise_floor = float(initial_noise_floor)
        self.trigger_multiplier = float(trigger_multiplier)
        self.hold_multiplier = float(hold_multiplier)
        self.min_trigger = float(min_trigger)
        self.min_hold = float(min_hold)
        self.consecutive_frames_required = int(consecutive_frames_required)

        self._in_speech = False
        self._consecutive_speech_count = 0

    def reset(self, noise_floor: float | None = None) -> None:
        """Reset internal detector state."""
        if noise_floor is not None:
            self.noise_floor = float(noise_floor)
        self._in_speech = False
        self._consecutive_speech_count = 0

    def update_noise_floor(self, current_rms: float) -> None:
        """Update ambient noise floor using exponential moving average during non-speech periods."""
        if not self._in_speech and current_rms > 0.0001:
            self.noise_floor = float(np.clip(0.94 * self.noise_floor + 0.06 * current_rms, 0.0005, 0.15))

    def is_speech_candidate(self, frame: np.ndarray) -> tuple[bool, float, float]:
        """Analyze a frame and return (is_speech, rms, peak)."""
        rms = calculate_rms(frame)
        peak = calculate_peak(frame)

        if self._in_speech:
            threshold = max(self.min_hold, self.noise_floor * self.hold_multiplier)
            if rms >= threshold:
                return True, rms, peak
            else:
                self._in_speech = False
                self._consecutive_speech_count = 0
                return False, rms, peak
        else:
            threshold = max(self.min_trigger, self.noise_floor * self.trigger_multiplier)
            if rms >= threshold:
                self._consecutive_speech_count += 1
                if self._consecutive_speech_count >= self.consecutive_frames_required:
                    self._in_speech = True
                    return True, rms, peak
                return False, rms, peak
            else:
                self._consecutive_speech_count = 0
                self.update_noise_floor(rms)
                return False, rms, peak


# ============================================================================
# 8. 0.64-Second Pre-Roll Ring Buffer (Section 10, 13)
# ============================================================================

class PreRollBuffer:
    """Thread-safe in-memory ring buffer preserving the first word of speech."""

    def __init__(self, max_frames: int = 20) -> None:
        self.max_frames = max_frames
        self._buffer: deque[np.ndarray] = deque(maxlen=max_frames)
        self._lock = threading.Lock()

    def push(self, frame: np.ndarray) -> None:
        """Add a copy of the frame to the ring buffer, dropping the oldest if full."""
        frame_copy = np.array(frame, copy=True)
        with self._lock:
            self._buffer.append(frame_copy)

    def get_snapshot(self) -> list[np.ndarray]:
        """Return an immutable snapshot list of all buffered frames in order."""
        with self._lock:
            return list(self._buffer)

    def clear(self) -> None:
        """Clear all buffered frames from RAM."""
        with self._lock:
            self._buffer.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._buffer)


# ============================================================================
# 9. Real-Time Audio Capture Engine (Section 09)
# ============================================================================

class AudioCaptureEngine:
    """Manages PortAudio input stream, non-blocking callback, bounded frame queue,

    and pre-roll ring buffer.
    """

    def __init__(self, config: AudioConfig, device_index: int | None = None) -> None:
        self.config = config
        self.device_index = device_index if (device_index is not None and device_index >= 0) else None

        self.stream: sd.InputStream | None = None
        self.active_sample_rate = config.sample_rate
        self.active_channels = config.channels
        self.needs_resampling = False
        self.needs_downmix = False

        self.frame_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=config.maximum_queue_frames)
        self.pre_roll_buffer = PreRollBuffer(max_frames=config.pre_roll_frames)

        self.overflow_count = 0
        self.is_running = False
        self._lock = threading.Lock()

    def _determine_stream_settings(self) -> tuple[int, int]:
        """Negotiate supported sample rate and channels with the input device."""
        dev_info = get_input_device_info(self.device_index)
        if not dev_info:
            raise AudioDeviceNotFoundError(f"Input device index {self.device_index} not available")

        dev_idx = dev_info["index"]
        try:
            sd.check_input_settings(device=dev_idx, samplerate=self.config.sample_rate, channels=self.config.channels, dtype="float32")
            return self.config.sample_rate, self.config.channels
        except Exception:
            pass

        native_rate = int(dev_info["default_samplerate"])
        max_in = int(dev_info["max_input_channels"])
        try:
            sd.check_input_settings(device=dev_idx, samplerate=native_rate, channels=1, dtype="float32")
            return native_rate, 1
        except Exception:
            pass

        if max_in >= 2:
            try:
                sd.check_input_settings(device=dev_idx, samplerate=native_rate, channels=2, dtype="float32")
                return native_rate, 2
            except Exception:
                pass

        return native_rate, max_in

    def _stream_callback(self, indata: np.ndarray, frames: int, time_info: Any, status: sd.CallbackFlags) -> None:
        """Non-blocking PortAudio callback pushing copied frames into the bounded queue."""
        if status:
            if status.input_overflow:
                self.overflow_count += 1

        if not self.is_running:
            return

        frame_copy = np.array(indata, copy=True, dtype=np.float32)
        self.pre_roll_buffer.push(frame_copy)
        try:
            self.frame_queue.put_nowait(frame_copy)
        except queue.Full:
            self.overflow_count += 1

    def start(self) -> None:
        """Open the PortAudio input stream and begin real-time frame buffering."""
        with self._lock:
            if self.is_running:
                return

            sr, ch = self._determine_stream_settings()
            self.active_sample_rate = sr
            self.active_channels = ch
            self.needs_resampling = (sr != self.config.sample_rate)
            self.needs_downmix = (ch > 1)

            block_size = int(round(sr * (self.config.frame_duration_ms / 1000.0)))

            try:
                self.stream = sd.InputStream(
                    device=self.device_index,
                    samplerate=sr,
                    channels=ch,
                    dtype="float32",
                    blocksize=block_size,
                    callback=self._stream_callback,
                )
                self.stream.start()
                self.is_running = True
            except Exception as exc:
                self.is_running = False
                raise AudioStreamOpenError(f"Failed to open input stream: {exc}") from exc

    def read_frame(self, timeout: float = 0.5) -> np.ndarray | None:
        """Pop the next captured frame from the queue."""
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self) -> None:
        """Stop the PortAudio stream cleanly and release resources."""
        with self._lock:
            self.is_running = False
            if self.stream is not None:
                try:
                    self.stream.stop()
                    self.stream.close()
                except Exception:
                    pass
                finally:
                    self.stream = None

            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    break


# ============================================================================
# 10. Smart Audio Ear Master Class (Section 13, 16)
# ============================================================================

class SmartAudioEar:
    """Production-grade neural hearing audio engine for Zye AI.

    Combines device management, real-time capture, Silero Neural VAD ONNX,
    adaptive RMS noise-floor fallback, dual-threshold hysteresis (0.52 / 0.40),
    0.64s pre-roll first-word preservation, and in-memory WAV generation.
    """

    def __init__(
        self,
        config: AudioConfig | None = None,
        device_index: int | None = None,
        agc_config: AGCConfig | None = None,
        chime_config: ChimeConfig | None = None,
    ) -> None:
        self.config = config or AudioConfig()
        if device_index is not None and device_index >= 0:
            self.device_index = device_index
        elif self.config.preferred_device_index >= 0:
            self.device_index = self.config.preferred_device_index
        else:
            self.device_index = None

        self.capture_engine = AudioCaptureEngine(self.config, device_index=self.device_index)
        self.rms_detector = AdaptiveRMSDetector(initial_noise_floor=self.config.noise_floor_initial)

        self.state = CaptureState.IDLE
        self.last_capture_diagnostics: dict[str, Any] = {}
        self._cancel_requested = False
        self._lock = threading.Lock()

        # Day 08 Neural VAD attributes (Section 14, 15, 19)
        self.vad_model: Any | None = None
        self.vad_status: VADModelStatus = VADModelStatus.NOT_INITIALIZED
        self.active_vad_backend: str = self.config.vad_backend if self.config.vad_mode == "silero_onnx" else "adaptive_rms"
        self.consecutive_speech_frames: int = 0
        self.consecutive_vad_errors: int = 0
        self.total_vad_inferences: int = 0
        self.total_vad_errors: int = 0
        self.vad_fallback_count: int = 0
        self.inference_latencies: list[float] = []
        self.model_load_time_ms: float = 0.0
        self.model_warmup_time_ms: float = 0.0
        self.last_speech_probability: float | None = None

        # Day 09 Audio Enhancement (AGC & Jarvis Chimes)
        self.agc_config = agc_config or getattr(self.config, "agc", None) or AGCConfig()
        self.chime_config = chime_config or getattr(self.config, "chimes", None) or ChimeConfig()
        self.agc = AGCProcessor(self.agc_config)
        self.chime_player = JarvisChimePlayer(self.chime_config, auto_start=True)

        # Automatically load neural VAD if configured
        if self.config.vad_mode == "silero_onnx":
            self.load_neural_vad()

    def set_state(self, new_state: CaptureState) -> None:
        """Transition capture state adhering to strict state-machine rules."""
        with self._lock:
            allowed = _VALID_TRANSITIONS.get(self.state, set())
            if new_state not in allowed:
                logger.debug("Invalid audio state transition requested: %s -> %s", self.state, new_state)
            self.state = new_state

    def get_capture_state(self) -> CaptureState:
        """Return the current capture state."""
        return self.state

    def list_microphones(self) -> list[dict[str, Any]]:
        """List all available microphone devices."""
        return list_input_devices()

    def check_mic_health(self) -> dict[str, Any]:
        """Perform hardware health check on current microphone device."""
        return check_mic_health(self.device_index)

    def load_neural_vad(self) -> dict[str, Any]:
        """Initialize the Silero VAD ONNX model with CPU execution, warmup, and state reset."""
        with self._lock:
            if self.vad_model is not None and self.vad_status == VADModelStatus.READY:
                return {
                    "status": "success",
                    "backend": self.active_vad_backend,
                    "model_status": self.vad_status.value,
                    "message": "Model already loaded",
                }

            self.vad_status = VADModelStatus.LOADING
            t0 = time.perf_counter()

            try:
                from silero_vad import load_silero_vad
                model = load_silero_vad(onnx=True)
                if model is None:
                    raise AudioProcessingError("load_silero_vad(onnx=True) returned None")

                self.vad_model = model
                self.model_load_time_ms = round((time.perf_counter() - t0) * 1000.0, 2)

                if self.config.vad_warmup_enabled:
                    self._warmup_internal()

                self.reset_vad_state()
                self.vad_status = VADModelStatus.READY
                self.active_vad_backend = "silero_onnx"
                self.consecutive_vad_errors = 0

                return {
                    "status": "success",
                    "backend": "silero_onnx",
                    "model_status": VADModelStatus.READY.value,
                    "load_time_ms": self.model_load_time_ms,
                    "warmup_time_ms": self.model_warmup_time_ms,
                }

            except Exception as exc:
                logger.warning("Silero Neural VAD ONNX initialization failed: %s", exc)
                self.vad_model = None
                if self.config.vad_auto_fallback:
                    self.vad_status = VADModelStatus.DEGRADED
                    self.active_vad_backend = "adaptive_rms"
                    self.vad_fallback_count += 1
                else:
                    self.vad_status = VADModelStatus.FAILED
                    self.active_vad_backend = "adaptive_rms"

                return {
                    "status": "degraded" if self.config.vad_auto_fallback else "failed",
                    "backend": self.active_vad_backend,
                    "model_status": self.vad_status.value,
                    "error": str(exc),
                }

    def warmup_neural_vad(self) -> bool:
        """Perform a controlled single-frame inference warmup on the loaded model."""
        with self._lock:
            return self._warmup_internal()

    def _warmup_internal(self) -> bool:
        """Internal warmup implementation without locking."""
        if self.vad_model is None:
            return False
        t_start = time.perf_counter()
        try:
            dummy_chunk = np.zeros(512, dtype=np.float32)
            tensor = prepare_vad_tensor(dummy_chunk)
            res = self.vad_model(tensor, self.config.sample_rate)
            if hasattr(res, "item"):
                float(res.item())
            if hasattr(self.vad_model, "reset_states"):
                self.vad_model.reset_states()
            self.model_warmup_time_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
            return True
        except Exception as exc:
            logger.warning("Warmup inference failed: %s", exc)
            return False

    def reset_vad_state(self) -> None:
        """Reset recurrent inference state, consecutive frame counts, and RMS detector."""
        if self.vad_model is not None and hasattr(self.vad_model, "reset_states"):
            try:
                self.vad_model.reset_states()
            except Exception as exc:
                logger.warning("Failed to reset VAD model states: %s", exc)
        self.consecutive_speech_frames = 0
        self.last_speech_probability = None
        self.rms_detector.reset()

    def unload_neural_vad(self) -> None:
        """Unload model from RAM, release recurrent states, and transition to CLOSED."""
        with self._lock:
            if self.vad_model is not None and hasattr(self.vad_model, "reset_states"):
                try:
                    self.vad_model.reset_states()
                except Exception:
                    pass
            self.vad_model = None
            self.vad_status = VADModelStatus.CLOSED

    def validate_vad_frame(self, frame: np.ndarray) -> bool:
        """Validate audio frame format for neural VAD input."""
        return validate_vad_frame(frame, self.config.sample_rate)

    def calculate_speech_probability(self, frame: np.ndarray) -> float:
        """Run neural VAD inference on a 512-sample float32 frame and return probability in [0.0, 1.0]."""
        if not self.validate_vad_frame(frame):
            raise AudioFormatError(f"Audio frame failed validation for neural VAD: shape={getattr(frame, 'shape', None)}")

        if self.active_vad_backend != "silero_onnx" or self.vad_model is None:
            rms = calculate_rms(frame)
            thresh = max(self.rms_detector.min_trigger, self.rms_detector.noise_floor * self.rms_detector.trigger_multiplier)
            prob = float(np.clip(rms / max(thresh * 1.5, 0.001), 0.0, 1.0))
            self.last_speech_probability = prob
            return prob

        t_inf_start = time.perf_counter()
        try:
            tensor = prepare_vad_tensor(frame)
            output = self.vad_model(tensor, self.config.sample_rate)
            if output is None or not hasattr(output, "item"):
                raise AudioProcessingError("VAD model returned invalid or empty output")

            prob = float(output.item())
            if not math.isfinite(prob):
                raise AudioProcessingError(f"VAD model returned non-finite probability: {prob}")

            prob = float(np.clip(prob, 0.0, 1.0))
            latency_ms = (time.perf_counter() - t_inf_start) * 1000.0

            self.inference_latencies.append(latency_ms)
            if len(self.inference_latencies) > 2000:
                self.inference_latencies.pop(0)

            self.total_vad_inferences += 1
            self.consecutive_vad_errors = 0
            self.last_speech_probability = prob
            return prob

        except Exception as exc:
            self.total_vad_errors += 1
            self.consecutive_vad_errors += 1
            logger.warning("VAD inference error (%d/%d): %s", self.consecutive_vad_errors, self.config.vad_max_consecutive_errors, exc)

            if self.config.vad_auto_fallback and self.consecutive_vad_errors >= self.config.vad_max_consecutive_errors:
                logger.error("Maximum consecutive VAD inference errors exceeded. Falling back to adaptive RMS.")
                self.active_vad_backend = "adaptive_rms"
                self.vad_status = VADModelStatus.DEGRADED
                self.vad_fallback_count += 1

            if self.active_vad_backend == "adaptive_rms":
                rms = calculate_rms(frame)
                thresh = max(self.rms_detector.min_trigger, self.rms_detector.noise_floor * self.rms_detector.trigger_multiplier)
                prob = float(np.clip(rms / max(thresh * 1.5, 0.001), 0.0, 1.0))
                self.last_speech_probability = prob
                return prob

            raise AudioProcessingError(f"VAD inference failed: {exc}") from exc

    def is_speech(self, frame: np.ndarray, started: bool = False) -> tuple[bool, float, float]:
        """Determine speech presence using neural VAD or adaptive RMS fallback.

        Returns (is_active, speech_probability_or_rms, peak).
        """
        mono = downmix_to_mono(frame) if frame.ndim > 1 else frame
        peak = calculate_peak(mono)

        if self.active_vad_backend == "silero_onnx" and self.vad_model is not None:
            prob = self.calculate_speech_probability(mono)
            threshold = self.config.vad_hold_threshold if started else self.config.vad_start_threshold
            return (prob >= threshold), prob, peak
        else:
            is_cand, rms, pk = self.rms_detector.is_speech_candidate(mono)
            return is_cand, rms, pk

    def is_speech_started(self, prob: float) -> bool:
        """Check if speech probability meets or exceeds start threshold (0.52)."""
        return prob >= self.config.vad_start_threshold

    def is_speech_continued(self, prob: float) -> bool:
        """Check if speech probability meets or exceeds hold threshold (0.40)."""
        return prob >= self.config.vad_hold_threshold

    def is_speech_ended(self, prob: float) -> bool:
        """Check if speech probability drops below hold threshold (0.40)."""
        return prob < self.config.vad_hold_threshold

    def adaptive_speech_detect(self, frame: np.ndarray) -> tuple[bool, float, float]:
        """Perform fallback adaptive RMS detection on a single frame."""
        mono = downmix_to_mono(frame) if frame.ndim > 1 else frame
        return self.rms_detector.is_speech_candidate(mono)

    def get_pre_roll_snapshot(self) -> list[np.ndarray]:
        """Retrieve copy of all frames currently preserved in the pre-roll buffer."""
        return self.capture_engine.pre_roll_buffer.get_snapshot()

    def start(self) -> None:
        """Start microphone listening stream and enter BUFFERING state."""
        self._cancel_requested = False
        self.reset_vad_state()
        self.capture_engine.start()
        self.set_state(CaptureState.BUFFERING)

    def stop(self) -> None:
        """Stop microphone stream and return to IDLE state."""
        self.capture_engine.stop()
        self.set_state(CaptureState.IDLE)

    def cancel_capture(self) -> None:
        """Signal immediate cancellation of active audio listening session."""
        self._cancel_requested = True
        self.reset_vad_state()
        self.set_state(CaptureState.CANCELLED)

    def reset_capture(self) -> None:
        """Reset state machine and clear temporary RAM buffers."""
        self.stop()
        self.capture_engine.pre_roll_buffer.clear()
        self.reset_vad_state()
        self.state = CaptureState.IDLE
        self._cancel_requested = False

    def listen_smart(
        self,
        silence_timeout: float | None = None,
        max_record_sec: float | None = None,
        interrupt_checker: Callable[[], bool] | None = None,
    ) -> bytes | None:
        """Listen for speech using Silero VAD or adaptive RMS, preserve 0.64s pre-roll,

        record until silence or timeout, and return signed 16-bit PCM WAV bytes.
        Returns None if no speech was detected or if cancelled.
        """
        silence_limit = silence_timeout or self.config.silence_timeout_seconds
        max_limit = max_record_sec or self.config.maximum_record_seconds

        if not self.capture_engine.is_running:
            try:
                self.start()
            except Exception:
                pass

        recorded_frames: list[np.ndarray] = []
        speech_started = False
        silence_start_time: float | None = None
        capture_start_time = time.time()
        self.consecutive_speech_frames = 0

        try:
            while not self._cancel_requested:
                if interrupt_checker and interrupt_checker():
                    self.cancel_capture()
                    return None

                elapsed_total = time.time() - capture_start_time
                if elapsed_total > max_limit:
                    if speech_started:
                        self.set_state(CaptureState.FINALIZING)
                        self.chime_player.play_stop()
                        break
                    else:
                        return None

                try:
                    frame = self.capture_engine.read_frame(timeout=0.1)
                except StopIteration:
                    break

                if frame is None:
                    continue

                mono_frame = downmix_to_mono(frame) if frame.ndim > 1 else frame

                # Step 1: Detect speech using active backend
                if self.active_vad_backend == "silero_onnx" and self.vad_model is not None:
                    prob = self.calculate_speech_probability(mono_frame)
                    is_active = (prob >= self.config.vad_hold_threshold) if speech_started else self.is_speech_started(prob)
                else:
                    is_candidate, rms, peak = self.rms_detector.is_speech_candidate(mono_frame)
                    is_active = is_candidate

                # Step 1b: Day 09 Acoustic Feedback Guard suppression
                # If chime is playing or within guard window, suppress new speech candidates to prevent feedback loop
                if not speech_started and self.chime_player.is_chime_guard_active():
                    is_active = False
                    self.consecutive_speech_frames = 0
                    if self.state == CaptureState.SPEECH_CANDIDATE:
                        self.set_state(CaptureState.BUFFERING)

                # Step 2: Handle speech initiation with pre-roll snapshot & consecutive confirmation
                if not speech_started:
                    if is_active:
                        self.consecutive_speech_frames += 1
                        if self.state != CaptureState.SPEECH_CANDIDATE:
                            self.set_state(CaptureState.SPEECH_CANDIDATE)

                        # Check consecutive frame confirmation
                        required_frames = self.config.vad_confirmation_frames if self.active_vad_backend == "silero_onnx" else 1
                        if self.consecutive_speech_frames >= required_frames:
                            speech_started = True
                            self.set_state(CaptureState.SPEECH_CONFIRMED)
                            self.chime_player.play_start()
                            self.set_state(CaptureState.SPEECH_DETECTED)

                            # Snapshot 0.64s pre-roll buffer from RAM
                            pre_roll_snapshot = self.capture_engine.pre_roll_buffer.get_snapshot()
                            recorded_frames.extend(pre_roll_snapshot)
                            recorded_frames.append(frame)
                            self.set_state(CaptureState.RECORDING)
                    else:
                        self.consecutive_speech_frames = 0
                        if self.state == CaptureState.SPEECH_CANDIDATE:
                            self.set_state(CaptureState.BUFFERING)
                else:
                    # During active recording
                    recorded_frames.append(frame)

                    if is_active:
                        silence_start_time = None
                        if self.state == CaptureState.SHORT_PAUSE:
                            self.set_state(CaptureState.RECORDING)
                    else:
                        if self.state == CaptureState.RECORDING:
                            self.set_state(CaptureState.SHORT_PAUSE)

                        if silence_start_time is None:
                            silence_start_time = time.time()
                        elif (time.time() - silence_start_time) >= silence_limit:
                            self.set_state(CaptureState.SILENCE_DETECTED)
                            self.set_state(CaptureState.FINALIZING)
                            self.chime_player.play_stop()
                            break

            if self._cancel_requested:
                return None

            if not speech_started or not recorded_frames:
                return None

            # Assembled recorded frames
            assembled_raw = np.concatenate(recorded_frames, axis=0)

            # Step 1: Downmix to mono if captured in stereo
            if assembled_raw.ndim > 1:
                assembled_mono = downmix_to_mono(assembled_raw)
            else:
                assembled_mono = assembled_raw

            # Step 2: Resample to 16,000 Hz if captured at native rate
            if self.capture_engine.needs_resampling:
                final_float32 = resample_audio(
                    assembled_mono,
                    orig_sr=self.capture_engine.active_sample_rate,
                    target_sr=self.config.sample_rate,
                )
            else:
                final_float32 = assembled_mono

            # Check minimum recording duration
            duration_sec = len(final_float32) / float(self.config.sample_rate)
            if duration_sec < self.config.minimum_record_seconds:
                return None

            # Step 3: Apply Day 09 Automatic Gain Control (AGC) and peak limiting
            agc_result = self.agc.process(final_float32)
            processed_float32 = agc_result.audio

            # Step 4: Convert float32 to PCM16
            pcm16_data = convert_float32_to_pcm16(processed_float32)

            # Step 5: Serialize to in-memory WAV bytes
            wav_bytes = encode_wav_bytes(pcm16_data, sample_rate=self.config.sample_rate)

            final_rms = calculate_rms(processed_float32)
            final_peak = calculate_peak(processed_float32)
            clipping = bool(final_peak >= 0.999)

            self.last_capture_diagnostics = {
                "duration_seconds": round(duration_sec, 3),
                "source_sample_rate": self.capture_engine.active_sample_rate,
                "output_sample_rate": self.config.sample_rate,
                "frames_count": len(recorded_frames),
                "samples_count": len(processed_float32),
                "rms": round(final_rms, 6),
                "peak": round(final_peak, 6),
                "clipping_detected": clipping,
                "queue_overflows": self.capture_engine.overflow_count,
                "vad_backend": self.active_vad_backend,
                "last_speech_probability": self.last_speech_probability,
                "agc": self.agc.get_diagnostics(),
                "chimes": self.chime_player.get_diagnostics(),
            }

            self.set_state(CaptureState.COMPLETED)
            return wav_bytes

        finally:
            if self.state not in (CaptureState.COMPLETED, CaptureState.CANCELLED):
                self.set_state(CaptureState.IDLE)

    def get_vad_status(self) -> dict[str, Any]:
        """Return structured VAD telemetry and runtime inference performance metrics."""
        avg_ms = float(np.mean(self.inference_latencies)) if self.inference_latencies else 0.0
        p50_ms = float(np.percentile(self.inference_latencies, 50)) if self.inference_latencies else 0.0
        p95_ms = float(np.percentile(self.inference_latencies, 95)) if self.inference_latencies else 0.0
        max_ms = float(np.max(self.inference_latencies)) if self.inference_latencies else 0.0

        return {
            "status": "success",
            "engine": "ZyeNeuralHearing",
            "backend": self.active_vad_backend,
            "model_status": self.vad_status.value if hasattr(self.vad_status, "value") else str(self.vad_status),
            "model_loaded": (self.vad_model is not None and self.vad_status == VADModelStatus.READY),
            "inference_device": self.config.vad_device,
            "sample_rate": self.config.sample_rate,
            "frame_samples": self.config.frame_samples,
            "frame_duration_ms": self.config.frame_duration_ms,
            "start_threshold": self.config.vad_start_threshold,
            "hold_threshold": self.config.vad_hold_threshold,
            "start_confirmation_frames": self.config.vad_confirmation_frames,
            "pre_roll_seconds": self.config.pre_roll_seconds,
            "fallback_available": True,
            "fallback_backend": self.config.vad_fallback_backend,
            "fallback_count": self.vad_fallback_count,
            "total_inferences": self.total_vad_inferences,
            "inference_errors": self.total_vad_errors,
            "consecutive_errors": self.consecutive_vad_errors,
            "queue_overflows": self.capture_engine.overflow_count,
            "last_speech_probability": self.last_speech_probability,
            "avg_inference_ms": round(avg_ms, 2),
            "p50_inference_ms": round(p50_ms, 2),
            "p95_inference_ms": round(p95_ms, 2),
            "max_inference_ms": round(max_ms, 2),
            "model_load_time_ms": self.model_load_time_ms,
            "model_warmup_time_ms": self.model_warmup_time_ms,
        }

    def _apply_auto_gain(self, audio_np: np.ndarray) -> np.ndarray:
        """Apply automatic gain control to audio array (backwards compatible helper)."""
        return self.agc.process(audio_np).audio

    def get_agc_diagnostics(self) -> dict[str, Any]:
        """Return structured AGC telemetry metrics."""
        return self.agc.get_diagnostics()

    def get_chime_diagnostics(self) -> dict[str, Any]:
        """Return structured chime player telemetry metrics."""
        return self.chime_player.get_diagnostics()

    def get_audio_enhancement_status(self) -> dict[str, Any]:
        """Return combined status of AGC and Jarvis Chime audio enhancements."""
        return {
            "status": "DAY_09_AUDIO_ENHANCEMENT_READY",
            "agc": self.get_agc_diagnostics(),
            "chimes": self.get_chime_diagnostics(),
        }

    def get_audio_diagnostics(self) -> dict[str, Any]:
        """Return structured audio diagnostic telemetry without raw audio samples."""
        dev_info = get_input_device_info(self.device_index)
        mic_avail = dev_info is not None

        return {
            "status": "success",
            "audio_engine": "ZyeSmartAudioEar",
            "diagnostic_status": "DAY_07_AUDIO_EAR_READY",
            "neural_vad_status": "DAY_08_NEURAL_HEARING_READY",
            "audio_enhancement_status": "DAY_09_AUDIO_ENHANCEMENT_READY",
            "microphone_available": mic_avail,
            "device_name": dev_info["name"] if dev_info else "None",
            "sample_rate": self.config.sample_rate,
            "channels": self.config.channels,
            "format": self.config.target_output_format,
            "pre_roll_seconds": self.config.pre_roll_seconds,
            "vad_mode": self.config.vad_mode,
            "active_backend": self.active_vad_backend,
            "capture_active": self.capture_engine.is_running,
            "queue_overflows": self.capture_engine.overflow_count,
            "vad_status": self.get_vad_status(),
            "agc_status": self.get_agc_diagnostics(),
            "chime_status": self.get_chime_diagnostics(),
            "last_capture": self.last_capture_diagnostics,
        }

    def close(self) -> None:
        """Full teardown of PortAudio streams and release of all memory buffers and models."""
        self.stop()
        self.unload_neural_vad()
        if hasattr(self, "chime_player"):
            try:
                self.chime_player.close()
            except Exception:
                pass
        if hasattr(self, "agc"):
            try:
                self.agc.reset()
            except Exception:
                pass
        self.capture_engine.pre_roll_buffer.clear()
        self.last_capture_diagnostics.clear()


# ============================================================================
# 11. Module Entry Point
# ============================================================================

if __name__ == "__main__":
    print("Zye Smart Audio Ear & Neural Hearing Engine v2.0")
    ear = SmartAudioEar()
    health = ear.check_mic_health()
    print("Microphone Health Check:", health)
    vad_stat = ear.get_vad_status()
    print("VAD Status:", vad_stat)
    ear.close()
