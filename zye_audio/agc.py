#!/usr/bin/env python3
"""
ZYE AI — Automatic Gain Control (AGC) Engine v3.0
================================================

Advanced dynamic volume normalization, legacy peak normalization (0.85 target,
12.0x maximum boost), adaptive windowed RMS gain adjustment with attack/release
smoothing, peak limiting (0.95 ceiling), silence detection protection, and
zero-distortion float32 signal processing.

Operating System: Windows 10/11 x64
Target Format: 16,000 Hz, Mono, Float32 / Signed 16-bit PCM
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import math
import time
from typing import Any

import numpy as np

logger = logging.getLogger("zye_audio.agc")


# ============================================================================
# 1. Custom Exceptions
# ============================================================================

class AGCError(Exception):
    """Base exception for all AGC signal processing failures."""
    pass


class AGCConfigError(AGCError):
    """Raised when invalid AGC configuration parameters are specified."""
    pass


# ============================================================================
# 2. Data Models & Configuration (Section 05, 06, 07, 10)
# ============================================================================

@dataclass
class AGCConfig:
    """Master configuration for Automatic Gain Control and peak limiting."""
    enabled: bool = True
    mode: str = "peak_normalize"  # "peak_normalize" or "adaptive"
    target_peak: float = 0.85
    max_gain: float = 12.0
    min_gain: float = 0.50
    silence_threshold: float = 1e-5
    target_rms: float = 0.12
    window_ms: int = 20
    hop_ms: int = 10
    attack_ms: float = 10.0
    release_ms: float = 250.0
    limiter_peak: float = 0.95
    adaptive_mode_enabled: bool = False
    sample_rate: int = 16000

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate all configuration attributes strictly."""
        if not isinstance(self.enabled, bool):
            raise AGCConfigError("enabled must be a boolean")
        if self.mode not in ("peak_normalize", "adaptive"):
            raise AGCConfigError(f"mode must be 'peak_normalize' or 'adaptive', got {self.mode}")
        if not (0.0 < self.target_peak <= 1.0):
            raise AGCConfigError(f"target_peak must be in (0.0, 1.0], got {self.target_peak}")
        if self.max_gain < 1.0 or self.max_gain > 50.0:
            raise AGCConfigError(f"max_gain must be between 1.0 and 50.0, got {self.max_gain}")
        if self.min_gain <= 0.0 or self.min_gain > 1.0:
            raise AGCConfigError(f"min_gain must be in (0.0, 1.0], got {self.min_gain}")
        if self.silence_threshold < 0.0:
            raise AGCConfigError("silence_threshold must be non-negative")
        if self.target_rms <= 0.0 or self.target_rms > 1.0:
            raise AGCConfigError(f"target_rms must be in (0.0, 1.0], got {self.target_rms}")
        if self.window_ms <= 0 or self.window_ms > 1000:
            raise AGCConfigError(f"window_ms must be positive and <= 1000, got {self.window_ms}")
        if self.hop_ms <= 0 or self.hop_ms > self.window_ms:
            raise AGCConfigError(f"hop_ms must be positive and <= window_ms ({self.window_ms}), got {self.hop_ms}")
        if self.attack_ms <= 0.0 or self.release_ms <= 0.0:
            raise AGCConfigError("attack_ms and release_ms must be positive")
        if not (0.0 < self.limiter_peak <= 1.0):
            raise AGCConfigError(f"limiter_peak must be in (0.0, 1.0], got {self.limiter_peak}")
        if self.limiter_peak < self.target_peak:
            raise AGCConfigError(f"limiter_peak ({self.limiter_peak}) should not be less than target_peak ({self.target_peak})")
        if not isinstance(self.sample_rate, int) or self.sample_rate <= 0:
            raise AGCConfigError(f"sample_rate must be a positive integer, got {self.sample_rate}")


@dataclass(frozen=True)
class AGCResult:
    """Immutable structured result of an AGC normalization operation."""
    audio: np.ndarray
    mode: str
    applied_gain: float
    input_peak: float
    output_peak: float
    input_rms: float
    output_rms: float
    clipping_detected: bool
    silence_detected: bool
    processing_duration_ms: float
    status: str


# ============================================================================
# 3. AGC Processor Master Engine (Section 05, 06, 07, 08, 09, 10)
# ============================================================================

class AGCProcessor:
    """Advanced Automatic Gain Control and peak limiting processor."""

    def __init__(self, config: AGCConfig | None = None) -> None:
        self.config = config or AGCConfig()
        self.total_processed_frames = 0
        self.total_clipping_events = 0
        self.total_silence_events = 0
        self.last_diagnostics: dict[str, Any] = {}

    def calculate_peak(self, audio: np.ndarray) -> float:
        """Calculate peak absolute amplitude of an audio array."""
        if audio is None or len(audio) == 0:
            return 0.0
        flat = np.asarray(audio).reshape(-1)
        if not np.all(np.isfinite(flat)):
            raise AGCError("Audio array contains NaN or Inf values")
        return float(np.max(np.abs(flat)))

    def calculate_rms(self, audio: np.ndarray) -> float:
        """Calculate Root Mean Square (RMS) amplitude of an audio array."""
        if audio is None or len(audio) == 0:
            return 0.0
        flat = np.asarray(audio).reshape(-1)
        if not np.all(np.isfinite(flat)):
            raise AGCError("Audio array contains NaN or Inf values")
        mean_sq = float(np.mean(flat.astype(np.float64) ** 2))
        return float(np.sqrt(mean_sq))

    def calculate_gain(self, audio: np.ndarray) -> float:
        """Estimate required linear amplification factor based on target peak."""
        peak = self.calculate_peak(audio)
        if peak < self.config.silence_threshold:
            return 1.0
        return float(min(self.config.max_gain, self.config.target_peak / peak))

    def apply_peak_normalization(self, audio: np.ndarray) -> tuple[np.ndarray, float]:
        """Apply legacy peak normalization targeting 0.85 with 12x max gain."""
        if audio is None or len(audio) == 0:
            return np.array([], dtype=np.float32), 1.0

        arr = np.asarray(audio, dtype=np.float32)
        if not np.all(np.isfinite(arr)):
            raise AGCError("Audio array contains NaN or Inf values")

        peak = float(np.max(np.abs(arr)))
        if peak < self.config.silence_threshold:
            return np.array(arr, copy=True), 1.0

        gain = float(min(self.config.max_gain, self.config.target_peak / peak))
        boosted = arr * gain
        # Safety limiter
        boosted = np.clip(boosted, -self.config.limiter_peak, self.config.limiter_peak)
        return boosted, gain

    def apply_adaptive_gain(self, audio: np.ndarray) -> tuple[np.ndarray, float]:
        """Apply window-based adaptive RMS gain adjustment with attack/release smoothing."""
        if audio is None or len(audio) == 0:
            return np.array([], dtype=np.float32), 1.0

        arr = np.asarray(audio, dtype=np.float32)
        if not np.all(np.isfinite(arr)):
            raise AGCError("Audio array contains NaN or Inf values")

        total_samples = len(arr)
        peak = float(np.max(np.abs(arr)))
        if peak < self.config.silence_threshold:
            return np.array(arr, copy=True), 1.0

        sr = self.config.sample_rate
        win_size = max(16, int(round(sr * (self.config.window_ms / 1000.0))))
        hop_size = max(8, int(round(sr * (self.config.hop_ms / 1000.0))))

        # If audio is shorter than a single window, fall back to peak normalization
        if total_samples <= win_size:
            return self.apply_peak_normalization(arr)

        # 1. Window-based RMS calculation
        window_centers: list[int] = []
        raw_gains: list[float] = []

        for start in range(0, total_samples, hop_size):
            end = min(start + win_size, total_samples)
            chunk = arr[start:end]
            win_center = start + (len(chunk) // 2)
            window_centers.append(win_center)

            mean_sq = float(np.mean(chunk.astype(np.float64) ** 2))
            win_rms = math.sqrt(mean_sq)

            if win_rms < self.config.silence_threshold:
                desired_gain = 1.0
            else:
                desired_gain = self.config.target_rms / max(win_rms, 1e-6)
                desired_gain = max(self.config.min_gain, min(self.config.max_gain, desired_gain))

            raw_gains.append(desired_gain)

        if not raw_gains:
            return self.apply_peak_normalization(arr)

        # 2. Attack and release smoothing
        # Attack: gain decreases quickly when signal gets loud
        # Release: gain increases gradually when signal gets soft
        alpha_attack = math.exp(-self.config.hop_ms / max(1.0, self.config.attack_ms))
        alpha_release = math.exp(-self.config.hop_ms / max(1.0, self.config.release_ms))

        smoothed_gains: list[float] = [raw_gains[0]]
        for i in range(1, len(raw_gains)):
            prev = smoothed_gains[-1]
            target = raw_gains[i]
            if target < prev:
                # Attack phase (reducing gain)
                sm_gain = alpha_attack * prev + (1.0 - alpha_attack) * target
            else:
                # Release phase (increasing gain)
                sm_gain = alpha_release * prev + (1.0 - alpha_release) * target
            smoothed_gains.append(sm_gain)

        # 3. Interpolate smoothed gain envelope across all audio samples
        centers_arr = np.array(window_centers, dtype=np.float64)
        gains_arr = np.array(smoothed_gains, dtype=np.float64)
        all_indices = np.arange(total_samples, dtype=np.float64)

        gain_envelope = np.interp(all_indices, centers_arr, gains_arr).astype(np.float32)

        # Apply gain envelope
        boosted = arr * gain_envelope

        # 4. Peak safety limiter (prevent any overshoot above limiter_peak)
        boosted = self.apply_peak_limiter(boosted, limit=self.config.limiter_peak)

        avg_gain = float(np.mean(gain_envelope))
        return boosted, avg_gain

    def apply_peak_limiter(self, audio: np.ndarray, limit: float | None = None) -> np.ndarray:
        """Apply smooth peak limiter to guarantee absolute maximum amplitude."""
        if audio is None or len(audio) == 0:
            return np.array([], dtype=np.float32)

        arr = np.asarray(audio, dtype=np.float32)
        ceiling = limit if limit is not None else self.config.limiter_peak
        peak = float(np.max(np.abs(arr)))

        if peak > ceiling:
            attenuation = ceiling / peak
            arr = arr * attenuation

        return np.clip(arr, -ceiling, ceiling)

    def process(self, audio: np.ndarray, vad_metadata: dict[str, Any] | None = None) -> AGCResult:
        """Execute complete AGC pipeline on completed speech recording."""
        t0 = time.perf_counter()

        if audio is None or len(audio) == 0:
            empty_arr = np.array([], dtype=np.float32)
            res = AGCResult(
                audio=empty_arr,
                mode=self.config.mode,
                applied_gain=1.0,
                input_peak=0.0,
                output_peak=0.0,
                input_rms=0.0,
                output_rms=0.0,
                clipping_detected=False,
                silence_detected=True,
                processing_duration_ms=0.0,
                status="EMPTY_INPUT",
            )
            self._update_diagnostics(res)
            return res

        orig_shape = audio.shape
        orig_dtype = audio.dtype

        # Preserve 1D float32 representation
        arr = np.asarray(audio, dtype=np.float32)
        if not np.all(np.isfinite(arr)):
            raise AGCError("Audio input contains NaN or Inf values")

        in_peak = self.calculate_peak(arr)
        in_rms = self.calculate_rms(arr)

        if not self.config.enabled:
            # Pass-through when disabled
            duration_ms = (time.perf_counter() - t0) * 1000.0
            res = AGCResult(
                audio=np.array(arr, copy=True),
                mode="disabled",
                applied_gain=1.0,
                input_peak=round(in_peak, 6),
                output_peak=round(in_peak, 6),
                input_rms=round(in_rms, 6),
                output_rms=round(in_rms, 6),
                clipping_detected=(in_peak >= 0.999),
                silence_detected=(in_peak < self.config.silence_threshold),
                processing_duration_ms=round(duration_ms, 2),
                status="DISABLED",
            )
            self._update_diagnostics(res)
            return res

        # Check silence
        if in_peak < self.config.silence_threshold:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            self.total_silence_events += 1
            res = AGCResult(
                audio=np.array(arr, copy=True),
                mode=self.config.mode,
                applied_gain=1.0,
                input_peak=round(in_peak, 6),
                output_peak=round(in_peak, 6),
                input_rms=round(in_rms, 6),
                output_rms=round(in_rms, 6),
                clipping_detected=False,
                silence_detected=True,
                processing_duration_ms=round(duration_ms, 2),
                status="SILENCE_PROTECTED",
            )
            self._update_diagnostics(res)
            return res

        # Select mode
        if self.config.mode == "adaptive" or self.config.adaptive_mode_enabled:
            boosted, gain = self.apply_adaptive_gain(arr)
            mode_applied = "adaptive"
        else:
            boosted, gain = self.apply_peak_normalization(arr)
            mode_applied = "peak_normalize"

        # Reshape to original layout if needed
        if boosted.shape != orig_shape:
            boosted = boosted.reshape(orig_shape)

        out_peak = self.calculate_peak(boosted)
        out_rms = self.calculate_rms(boosted)
        clipping = bool(out_peak >= 0.999)
        if clipping:
            self.total_clipping_events += 1

        duration_ms = (time.perf_counter() - t0) * 1000.0
        self.total_processed_frames += 1

        res = AGCResult(
            audio=boosted,
            mode=mode_applied,
            applied_gain=round(gain, 4),
            input_peak=round(in_peak, 6),
            output_peak=round(out_peak, 6),
            input_rms=round(in_rms, 6),
            output_rms=round(out_rms, 6),
            clipping_detected=clipping,
            silence_detected=False,
            processing_duration_ms=round(duration_ms, 2),
            status="SUCCESS",
        )
        self._update_diagnostics(res)
        return res

    def _update_diagnostics(self, result: AGCResult) -> None:
        """Update internal diagnostic telemetry structure."""
        self.last_diagnostics = {
            "status": "success" if result.status in ("SUCCESS", "SILENCE_PROTECTED", "DISABLED") else "warning",
            "enabled": self.config.enabled,
            "mode": result.mode,
            "target_peak": self.config.target_peak,
            "max_gain": self.config.max_gain,
            "applied_gain": result.applied_gain,
            "input_peak": result.input_peak,
            "output_peak": result.output_peak,
            "input_rms": result.input_rms,
            "output_rms": result.output_rms,
            "clipping_detected": result.clipping_detected,
            "silence_detected": result.silence_detected,
            "processing_duration_ms": result.processing_duration_ms,
            "total_processed": self.total_processed_frames,
            "total_clippings": self.total_clipping_events,
            "total_silences": self.total_silence_events,
        }

    def get_diagnostics(self) -> dict[str, Any]:
        """Return structured AGC telemetry metrics."""
        if not self.last_diagnostics:
            return {
                "status": "ready",
                "enabled": self.config.enabled,
                "mode": self.config.mode,
                "target_peak": self.config.target_peak,
                "max_gain": self.config.max_gain,
                "applied_gain": 1.0,
                "input_peak": 0.0,
                "output_peak": 0.0,
                "input_rms": 0.0,
                "output_rms": 0.0,
                "clipping_detected": False,
                "silence_detected": False,
                "total_processed": self.total_processed_frames,
            }
        return dict(self.last_diagnostics)

    def reset(self) -> None:
        """Reset counters and diagnostic state."""
        self.total_processed_frames = 0
        self.total_clipping_events = 0
        self.total_silence_events = 0
        self.last_diagnostics.clear()
