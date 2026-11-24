#!/usr/bin/env python3
"""
ZYE AI — Audio Clarity Guard & Tool Authorization Gate v1.0
===========================================================

Protects system integrity by validating audio intelligibility before
submitting voice commands to tool-calling execution pipelines:
- Local audio preflight (WAV header, duration, clipping, RMS energy)
- Hard tool execution prohibition when speech is unclear or ambiguous
- Exact Tanglish clarification response: "Konjam clear-ah kekkala, thirumba solreengala?"
- Exemption for direct Alt+Z keyboard text commands
"""

from __future__ import annotations

import io
import json
import logging
import math
import wave
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger("zye_brain.clarity_guard")

EXACT_CLARIFICATION_MESSAGE = "Konjam clear-ah kekkala, thirumba solreengala?"


@dataclass
class ClarityConfig:
    """Configuration for audio clarity validation."""
    enabled: bool = True
    strict_mode: bool = True
    reject_empty_audio: bool = True
    reject_malformed_wav: bool = True
    block_tools_when_unclear: bool = True
    clarification_message: str = EXACT_CLARIFICATION_MESSAGE
    min_duration_seconds: float = 0.25
    max_duration_seconds: float = 35.0
    min_rms_threshold: float = 0.003
    max_clipping_ratio: float = 0.15


@dataclass
class ClarityAssessment:
    """Structured assessment of audio intelligibility."""
    is_clear: bool
    clarity: str  # "clear" | "unclear" | "incomplete" | "ambiguous"
    reason: str
    needs_clarification: bool
    preflight_passed: bool
    details: dict[str, Any]


class ZyeAudioClarityGuard:
    """
    Validates audio recording quality and enforces an unyielding safety boundary:
    If speech is ambiguous, muffled, or drowned in noise, refuse tool calling
    and request clarification.
    """

    def __init__(self, config: ClarityConfig | None = None) -> None:
        self.config = config or ClarityConfig()
        self.total_checked: int = 0
        self.total_unclear: int = 0
        self.total_rejected: int = 0

    def preflight_check(self, wav_bytes: bytes) -> tuple[bool, str, dict[str, Any]]:
        """
        Stage A: Validate basic WAV integrity, sample rate, duration, and energy.
        Returns (passed, failure_reason, metrics_dict).
        """
        if not wav_bytes or len(wav_bytes) < 44:
            return False, "Empty or truncated audio data", {"byte_count": len(wav_bytes) if wav_bytes else 0}

        # Check RIFF header
        if not (wav_bytes.startswith(b"RIFF") and b"WAVE" in wav_bytes[:16]):
            return False, "Malformed WAV header (missing RIFF/WAVE signature)", {"byte_count": len(wav_bytes)}

        try:
            with io.BytesIO(wav_bytes) as bio:
                with wave.open(bio, "rb") as wf:
                    channels = wf.getnchannels()
                    sample_rate = wf.getframerate()
                    sample_width = wf.getsampwidth()
                    num_frames = wf.getnframes()
                    raw_samples = wf.readframes(num_frames)

            duration = num_frames / float(sample_rate) if sample_rate > 0 else 0.0

            metrics = {
                "channels": channels,
                "sample_rate": sample_rate,
                "sample_width": sample_width,
                "num_frames": num_frames,
                "duration_seconds": round(duration, 3),
            }

            if self.config.reject_empty_audio and num_frames == 0:
                return False, "Audio recording contains 0 frames", metrics

            if duration < self.config.min_duration_seconds:
                return False, f"Audio too short ({duration:.2f}s < {self.config.min_duration_seconds}s)", metrics

            if duration > self.config.max_duration_seconds:
                return False, f"Audio exceeds maximum duration ({duration:.2f}s > {self.config.max_duration_seconds}s)", metrics

            # Check RMS energy and clipping if 16-bit PCM
            if sample_width == 2 and raw_samples:
                data = np.frombuffer(raw_samples, dtype=np.int16).astype(np.float32) / 32768.0
                rms = float(np.sqrt(np.mean(data ** 2))) if len(data) > 0 else 0.0
                clipping_count = int(np.sum(np.abs(data) >= 0.99))
                clipping_ratio = clipping_count / float(len(data)) if len(data) > 0 else 0.0

                metrics["rms"] = round(rms, 5)
                metrics["clipping_ratio"] = round(clipping_ratio, 4)

                if rms < self.config.min_rms_threshold:
                    return False, f"Near-silent audio (RMS {rms:.5f} < {self.config.min_rms_threshold})", metrics

                if clipping_ratio > self.config.max_clipping_ratio:
                    return False, f"Excessive clipping distortion ({clipping_ratio:.2%})", metrics

            return True, "Preflight checks passed", metrics

        except Exception as exc:
            return False, f"WAV parsing exception: {exc}", {"byte_count": len(wav_bytes)}

    def assess_audio(
        self,
        wav_bytes: bytes,
        gemini_assessment: dict[str, Any] | None = None,
    ) -> ClarityAssessment:
        """
        Evaluate full audio clarity combining Stage A preflight and Stage B AI assessment.
        """
        self.total_checked += 1

        if not self.config.enabled:
            return ClarityAssessment(
                is_clear=True,
                clarity="clear",
                reason="Clarity guard disabled in configuration",
                needs_clarification=False,
                preflight_passed=True,
                details={},
            )

        # Stage A: Preflight
        passed, reason, metrics = self.preflight_check(wav_bytes)
        if not passed:
            self.total_rejected += 1
            self.total_unclear += 1
            logger.info("Audio clarity preflight rejected: %s", reason)
            return ClarityAssessment(
                is_clear=False,
                clarity="unclear",
                reason=reason,
                needs_clarification=True,
                preflight_passed=False,
                details=metrics,
            )

        # Stage B: AI-based assessment if provided
        if gemini_assessment:
            clarity = str(gemini_assessment.get("clarity", "clear")).lower().strip()
            ai_reason = str(gemini_assessment.get("reason", "AI clarity assessment"))
            needs_clarification = bool(gemini_assessment.get("needs_clarification", False))

            if clarity != "clear" or needs_clarification:
                self.total_unclear += 1
                logger.info("AI clarity assessment marked audio as %s: %s", clarity, ai_reason)
                return ClarityAssessment(
                    is_clear=False,
                    clarity=clarity,
                    reason=ai_reason,
                    needs_clarification=True,
                    preflight_passed=True,
                    details=metrics,
                )

        return ClarityAssessment(
            is_clear=True,
            clarity="clear",
            reason="Audio validated successfully",
            needs_clarification=False,
            preflight_passed=True,
            details=metrics,
        )

    def can_execute_tools(self, assessment: ClarityAssessment, is_text_mode: bool = False) -> bool:
        """
        Hard safety check: Enforces tool execution prohibition if clarity failed.
        Alt+Z typed commands bypass microphone-only checks.
        """
        if is_text_mode:
            return True

        if not self.config.block_tools_when_unclear:
            return True

        return assessment.is_clear

    def get_clarification_response(self) -> str:
        """Return the exact Tanglish clarification prompt."""
        return self.config.clarification_message

    def get_status(self) -> dict[str, Any]:
        """Return structured diagnostics for clarity guard."""
        return {
            "enabled": self.config.enabled,
            "strict_mode": self.config.strict_mode,
            "block_tools_when_unclear": self.config.block_tools_when_unclear,
            "total_checked": self.total_checked,
            "total_unclear": self.total_unclear,
            "total_rejected": self.total_rejected,
            "clarification_message": self.config.clarification_message,
        }
