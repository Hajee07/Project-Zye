#!/usr/bin/env python3
"""
ZYE AI — Synthesized Jarvis Chime Player v3.0
============================================

Non-blocking, zero-asset programmatic audio feedback using pure NumPy sine waves
and sounddevice output streaming. Features two-tone ascending start chime,
two-tone descending stop chime, smooth linear crossfade envelopes, bounded playback
queue, serial playback execution, and an acoustic feedback guard window for Silero VAD.

Operating System: Windows 10/11 x64
Target Format: 16,000 Hz (or native output rate), Mono, Float32
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import math
import queue
import threading
import time
from typing import Any

import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None  # type: ignore

logger = logging.getLogger("zye_audio.chimes")


# ============================================================================
# 1. Custom Exceptions (Section 11, 14)
# ============================================================================

class ChimeError(Exception):
    """Base exception for chime synthesis and playback errors."""
    pass


class ChimeConfigError(ChimeError):
    """Raised when chime configuration parameters are invalid."""
    pass


class ChimeDeviceError(ChimeError):
    """Raised when audio output device validation or streaming fails."""
    pass


class ChimeQueueFullError(ChimeError):
    """Raised when chime playback queue exceeds maximum bounded capacity."""
    pass


# ============================================================================
# 2. Configuration Data Model (Section 11, 12)
# ============================================================================

@dataclass
class ChimeConfig:
    """Master configuration for Jarvis audio chimes and feedback guard."""
    enabled: bool = True
    sample_rate: int = 16000
    start_first_frequency: float = 540.0
    start_second_frequency: float = 820.0
    stop_first_frequency: float = 780.0
    stop_second_frequency: float = 480.0
    tone_duration_ms: float = 75.0
    amplitude: float = 0.12
    fade_duration_ms: float = 12.5
    vad_guard_ms: float = 250.0
    max_queue_size: int = 4
    device: int | str | None = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate chime configuration strictly."""
        if not isinstance(self.enabled, bool):
            raise ChimeConfigError("enabled must be a boolean")
        if not isinstance(self.sample_rate, int) or self.sample_rate <= 0:
            raise ChimeConfigError(f"sample_rate must be a positive integer, got {self.sample_rate}")
        for attr in ("start_first_frequency", "start_second_frequency", "stop_first_frequency", "stop_second_frequency"):
            val = getattr(self, attr)
            if not isinstance(val, (int, float)) or val <= 0.0 or val > 20000.0:
                raise ChimeConfigError(f"{attr} must be in range (0.0, 20000.0], got {val}")
        if not (0.0 < self.amplitude <= 1.0):
            raise ChimeConfigError(f"amplitude must be in (0.0, 1.0], got {self.amplitude}")
        if self.tone_duration_ms <= 0.0 or self.tone_duration_ms > 2000.0:
            raise ChimeConfigError(f"tone_duration_ms must be in (0.0, 2000.0], got {self.tone_duration_ms}")
        if self.fade_duration_ms < 0.0 or self.fade_duration_ms * 2.0 > self.tone_duration_ms:
            raise ChimeConfigError(
                f"fade_duration_ms ({self.fade_duration_ms}) * 2 must not exceed tone_duration_ms ({self.tone_duration_ms})"
            )
        if self.vad_guard_ms < 0.0 or self.vad_guard_ms > 5000.0:
            raise ChimeConfigError(f"vad_guard_ms must be in [0.0, 5000.0], got {self.vad_guard_ms}")
        if not isinstance(self.max_queue_size, int) or self.max_queue_size <= 0:
            raise ChimeConfigError(f"max_queue_size must be a positive integer, got {self.max_queue_size}")


# ============================================================================
# 3. Waveform Synthesis Functions (Section 12, 13)
# ============================================================================

def generate_tone(
    frequency: float,
    duration_ms: float,
    amplitude: float = 0.12,
    sample_rate: int = 16000,
    fade_duration_ms: float = 12.5,
) -> np.ndarray:
    """
    Generate a pure sine tone with linear fade-in and fade-out smoothing.

    Parameters:
        frequency: Tone frequency in Hz.
        duration_ms: Duration of tone in milliseconds.
        amplitude: Peak amplitude in range (0.0, 1.0].
        sample_rate: Sampling frequency in Hz.
        fade_duration_ms: Milliseconds of linear attack and release.

    Returns:
        1D float32 numpy array normalized to [-amplitude, +amplitude].
    """
    if duration_ms <= 0.0:
        return np.array([], dtype=np.float32)

    n_samples = int(round(sample_rate * (duration_ms / 1000.0)))
    if n_samples <= 0:
        return np.array([], dtype=np.float32)

    t = np.linspace(0.0, duration_ms / 1000.0, n_samples, endpoint=False, dtype=np.float32)
    waveform = (amplitude * np.sin(2.0 * np.pi * frequency * t)).astype(np.float32)

    # Apply linear fade envelope
    fade_samples = int(round(sample_rate * (fade_duration_ms / 1000.0)))
    if fade_samples > 0 and (fade_samples * 2) <= n_samples:
        fade_in = np.linspace(0.0, 1.0, fade_samples, endpoint=True, dtype=np.float32)
        fade_out = np.linspace(1.0, 0.0, fade_samples, endpoint=True, dtype=np.float32)
        waveform[:fade_samples] *= fade_in
        waveform[-fade_samples:] *= fade_out

    return waveform


def generate_start_chime(
    config: ChimeConfig | None = None,
    sample_rate: int | None = None,
) -> np.ndarray:
    """
    Synthesize the ascending Jarvis start chime (540 Hz -> 820 Hz).

    Returns:
        Concatenated 1D float32 numpy array of both tones (150 ms total).
    """
    cfg = config or ChimeConfig()
    sr = sample_rate or cfg.sample_rate
    t1 = generate_tone(
        frequency=cfg.start_first_frequency,
        duration_ms=cfg.tone_duration_ms,
        amplitude=cfg.amplitude,
        sample_rate=sr,
        fade_duration_ms=cfg.fade_duration_ms,
    )
    t2 = generate_tone(
        frequency=cfg.start_second_frequency,
        duration_ms=cfg.tone_duration_ms,
        amplitude=cfg.amplitude,
        sample_rate=sr,
        fade_duration_ms=cfg.fade_duration_ms,
    )
    return np.concatenate([t1, t2]).astype(np.float32)


def generate_stop_chime(
    config: ChimeConfig | None = None,
    sample_rate: int | None = None,
) -> np.ndarray:
    """
    Synthesize the descending Jarvis stop chime (780 Hz -> 480 Hz).

    Returns:
        Concatenated 1D float32 numpy array of both tones (150 ms total).
    """
    cfg = config or ChimeConfig()
    sr = sample_rate or cfg.sample_rate
    t1 = generate_tone(
        frequency=cfg.stop_first_frequency,
        duration_ms=cfg.tone_duration_ms,
        amplitude=cfg.amplitude,
        sample_rate=sr,
        fade_duration_ms=cfg.fade_duration_ms,
    )
    t2 = generate_tone(
        frequency=cfg.stop_second_frequency,
        duration_ms=cfg.tone_duration_ms,
        amplitude=cfg.amplitude,
        sample_rate=sr,
        fade_duration_ms=cfg.fade_duration_ms,
    )
    return np.concatenate([t1, t2]).astype(np.float32)


# ============================================================================
# 4. Jarvis Chime Player Master Engine (Section 13, 14, 15)
# ============================================================================

class JarvisChimePlayer:
    """
    Asynchronous, non-blocking chime playback engine with serial queuing,
    sounddevice integration, device validation, and feedback guard management.
    """

    def __init__(
        self,
        config: ChimeConfig | None = None,
        auto_start: bool = True,
    ) -> None:
        self.config = config or ChimeConfig()
        self._queue: queue.Queue[tuple[str, np.ndarray, float] | None] = queue.Queue(
            maxsize=self.config.max_queue_size
        )
        self._running = False
        self._worker_thread: threading.Thread | None = None
        self._guard_lock = threading.Lock()
        self._guard_until_timestamp: float = 0.0

        # Diagnostics & metrics
        self.start_chimes_played: int = 0
        self.stop_chimes_played: int = 0
        self.total_chimes_played: int = 0
        self.playback_errors: int = 0
        self.dropped_chimes: int = 0
        self.last_played_mode: str | None = None
        self.last_played_timestamp: float = 0.0

        # Pre-synthesize default waveforms in float32
        self._start_waveform = generate_start_chime(self.config)
        self._stop_waveform = generate_stop_chime(self.config)

        if auto_start and self.config.enabled:
            self.start()

    def start(self) -> None:
        """Start the background playback worker thread."""
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._playback_worker,
            name="ZyeChimePlayerWorker",
            daemon=True,
        )
        self._worker_thread.start()
        logger.debug("JarvisChimePlayer background worker started")

    def stop(self, timeout: float = 1.0) -> None:
        """Gracefully stop the background worker and drain pending items."""
        if not self._running:
            return
        self._running = False
        try:
            self._queue.put_nowait(None)
        except (queue.Full, Exception):
            pass

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)
        self._worker_thread = None
        logger.debug("JarvisChimePlayer stopped")

    def close(self) -> None:
        """Alias for stop() satisfying resource cleanup protocols."""
        self.stop()

    def __enter__(self) -> JarvisChimePlayer:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    # ------------------------------------------------------------------------
    # Device Validation (Section 14)
    # ------------------------------------------------------------------------

    def _resolve_output_device(self) -> int | None:
        """Resolve valid output audio device index with max_output_channels > 0."""
        if sd is None:
            return None
        try:
            if self.config.device is not None:
                return self.config.device
            devs = sd.query_devices()
            def_dev = sd.default.device
            out_idx = None
            if isinstance(def_dev, (list, tuple)) and len(def_dev) >= 2:
                out_idx = def_dev[1]
            elif isinstance(def_dev, int):
                out_idx = def_dev

            if out_idx is not None and 0 <= out_idx < len(devs):
                if devs[out_idx].get("max_output_channels", 0) > 0:
                    return out_idx

            # Find first device with output channels
            for idx, dev in enumerate(devs):
                if dev.get("max_output_channels", 0) > 0:
                    return idx
            return None
        except Exception:
            return None

    def validate_output_device(self) -> dict[str, Any]:
        """
        Inspect and validate default or configured audio output hardware.
        """
        if sd is None:
            return {
                "available": False,
                "device_name": "None (sounddevice not installed)",
                "error": "sounddevice library unavailable",
            }
        try:
            target_device = self._resolve_output_device()
            if target_device is None:
                return {
                    "available": False,
                    "device_name": "Unavailable",
                    "error": "No output-capable audio device detected",
                }
            device_info = sd.query_devices(device=target_device, kind="output")
            return {
                "available": True,
                "device_name": str(device_info.get("name", "Unknown")),
                "device_index": int(device_info.get("index", target_device)),
                "max_output_channels": int(device_info.get("max_output_channels", 0)),
                "default_samplerate": float(device_info.get("default_samplerate", 0.0)),
                "configured_samplerate": self.config.sample_rate,
            }
        except Exception as e:
            logger.debug(f"Audio output device validation failed: {e}")
            return {
                "available": False,
                "device_name": "Unavailable",
                "error": str(e),
            }

    # ------------------------------------------------------------------------
    # Playback API (Section 13, 14, 15)
    # ------------------------------------------------------------------------

    def play(self, mode: str) -> bool:
        """
        Enqueue a chime for non-blocking asynchronous playback.

        Parameters:
            mode: "start" for ascending detection chime, "stop" for descending finalization chime.

        Returns:
            True if successfully enqueued, False if dropped or disabled.
        """
        if not self.config.enabled:
            return False

        if not self._running:
            self.start()

        mode_clean = mode.strip().lower()
        if mode_clean == "start":
            waveform = self._start_waveform
        elif mode_clean == "stop":
            waveform = self._stop_waveform
        else:
            logger.warning(f"Unknown chime mode requested: {mode}")
            return False

        # Calculate exact duration for guard window
        duration_sec = len(waveform) / float(self.config.sample_rate)

        try:
            self._queue.put_nowait((mode_clean, waveform, duration_sec))
            return True
        except queue.Full:
            self.dropped_chimes += 1
            logger.warning("Chime playback queue full (max=%d); dropping chime '%s'", self.config.max_queue_size, mode_clean)
            return False

    def play_start(self) -> bool:
        """Convenience method to trigger Jarvis start chime."""
        return self.play("start")

    def play_stop(self) -> bool:
        """Convenience method to trigger Jarvis stop chime."""
        return self.play("stop")

    def play_sync(self, mode: str, timeout: float = 2.0) -> bool:
        """
        Play chime synchronously on the calling thread (for testing or CLI doctor).
        """
        if not self.config.enabled:
            return False

        mode_clean = mode.strip().lower()
        if mode_clean == "start":
            waveform = self._start_waveform
        elif mode_clean == "stop":
            waveform = self._stop_waveform
        else:
            return False

        duration_sec = len(waveform) / float(self.config.sample_rate)
        return self._play_waveform_internal(mode_clean, waveform, duration_sec)

    # ------------------------------------------------------------------------
    # Acoustic Feedback Guard Window (Section 15)
    # ------------------------------------------------------------------------

    def is_chime_guard_active(self) -> bool:
        """
        Return True if chime is actively playing or within the post-playback
        feedback guard window (vad_guard_ms).
        """
        with self._guard_lock:
            return time.perf_counter() < self._guard_until_timestamp

    def get_guard_remaining_ms(self) -> float:
        """Return remaining feedback guard duration in milliseconds."""
        with self._guard_lock:
            diff = self._guard_until_timestamp - time.perf_counter()
            return max(0.0, diff * 1000.0)

    # ------------------------------------------------------------------------
    # Internal Playback Loop
    # ------------------------------------------------------------------------

    def _playback_worker(self) -> None:
        """Background thread executing sequential chime playbacks."""
        while self._running:
            try:
                item = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if item is None:
                self._queue.task_done()
                break

            mode, waveform, duration_sec = item
            try:
                self._play_waveform_internal(mode, waveform, duration_sec)
            except Exception as e:
                self.playback_errors += 1
                logger.error(f"Unexpected error in chime playback worker: {e}", exc_info=True)
            finally:
                self._queue.task_done()

    def _play_waveform_internal(self, mode: str, waveform: np.ndarray, duration_sec: float) -> bool:
        """Internal routine that directly addresses sounddevice output."""
        # 1. Activate feedback guard window covering playback + post-guard
        guard_duration_sec = duration_sec + (self.config.vad_guard_ms / 1000.0)
        with self._guard_lock:
            self._guard_until_timestamp = max(
                self._guard_until_timestamp,
                time.perf_counter() + guard_duration_sec,
            )

        if sd is None:
            self.playback_errors += 1
            logger.warning("Cannot play chime: sounddevice library is not available")
            return False

        target_device = self._resolve_output_device()
        if target_device is None:
            self.playback_errors += 1
            logger.debug("Cannot play chime: no output device available")
            return False

        try:
            # Check channels of target device to prevent mono/stereo mismatch
            dev_info = sd.query_devices(device=target_device)
            max_out_channels = dev_info.get("max_output_channels", 1)
            if max_out_channels >= 2 and waveform.ndim == 1:
                play_waveform = np.column_stack([waveform, waveform])
            else:
                play_waveform = waveform

            # Play waveform
            sd.play(
                play_waveform,
                samplerate=self.config.sample_rate,
                device=target_device,
                blocking=True,
            )
            # Update metrics
            if mode == "start":
                self.start_chimes_played += 1
            elif mode == "stop":
                self.stop_chimes_played += 1
            self.total_chimes_played += 1
            self.last_played_mode = mode
            self.last_played_timestamp = time.time()
            return True
        except Exception as e:
            self.playback_errors += 1
            logger.debug("sounddevice chime playback note: %s", e)
            return False

    # ------------------------------------------------------------------------
    # Diagnostics & Telemetry (Section 14)
    # ------------------------------------------------------------------------

    def get_diagnostics(self) -> dict[str, Any]:
        """Return structured telemetry for doctor.py and system status."""
        device_diag = self.validate_output_device()
        return {
            "status": "ready" if device_diag.get("available") else "degraded",
            "enabled": self.config.enabled,
            "sample_rate": self.config.sample_rate,
            "start_first_frequency": self.config.start_first_frequency,
            "start_second_frequency": self.config.start_second_frequency,
            "stop_first_frequency": self.config.stop_first_frequency,
            "stop_second_frequency": self.config.stop_second_frequency,
            "tone_duration_ms": self.config.tone_duration_ms,
            "amplitude": self.config.amplitude,
            "fade_duration_ms": self.config.fade_duration_ms,
            "vad_guard_ms": self.config.vad_guard_ms,
            "guard_active": self.is_chime_guard_active(),
            "guard_remaining_ms": round(self.get_guard_remaining_ms(), 1),
            "start_chimes_played": self.start_chimes_played,
            "stop_chimes_played": self.stop_chimes_played,
            "total_chimes_played": self.total_chimes_played,
            "playback_errors": self.playback_errors,
            "dropped_chimes": self.dropped_chimes,
            "last_played_mode": self.last_played_mode,
            "worker_alive": bool(self._worker_thread and self._worker_thread.is_alive()),
            "output_device": device_diag,
        }

    def reset_metrics(self) -> None:
        """Reset playback counters."""
        self.start_chimes_played = 0
        self.stop_chimes_played = 0
        self.total_chimes_played = 0
        self.playback_errors = 0
        self.dropped_chimes = 0
        self.last_played_mode = None
