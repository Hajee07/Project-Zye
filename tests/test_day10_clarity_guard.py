#!/usr/bin/env python3
"""
ZYE AI — Day 10 Audio Clarity Guard Test Suite
==============================================
Tests for zye_brain.clarity_guard: ZyeAudioClarityGuard, ClarityAssessment,
audio preflight, tool authorization prohibition, and Tanglish clarification response.
"""

from __future__ import annotations

import io
import sys
import unittest
import wave
from pathlib import Path

import numpy as np

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zye_brain.clarity_guard import (
    ClarityAssessment,
    ClarityConfig,
    EXACT_CLARIFICATION_MESSAGE,
    ZyeAudioClarityGuard,
)


def _make_test_wav(
    duration_sec: float = 1.0,
    sample_rate: int = 16000,
    amplitude: float = 0.5,
) -> bytes:
    """Generate in-memory synthetic PCM16 WAV bytes."""
    num_samples = int(sample_rate * duration_sec)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False)
    sig = (np.sin(2 * np.pi * 440.0 * t) * amplitude * 32767).astype(np.int16)
    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(sig.tobytes())
    return bio.getvalue()


class TestZyeAudioClarityGuard(unittest.TestCase):
    """Test suite for Audio Clarity Guard & Tool Authorization Gate."""

    def setUp(self):
        self.guard = ZyeAudioClarityGuard()
        self.valid_wav = _make_test_wav(duration_sec=1.0, amplitude=0.5)

    def test_01_valid_wav_passes_preflight(self):
        passed, reason, metrics = self.guard.preflight_check(self.valid_wav)
        self.assertTrue(passed)
        self.assertEqual(metrics["channels"], 1)
        self.assertEqual(metrics["sample_rate"], 16000)
        self.assertAlmostEqual(metrics["duration_seconds"], 1.0, places=1)

    def test_02_empty_audio_rejected(self):
        passed, reason, _ = self.guard.preflight_check(b"")
        self.assertFalse(passed)
        self.assertIn("Empty", reason)

    def test_03_invalid_wav_header_rejected(self):
        passed, reason, _ = self.guard.preflight_check(b"NOT_A_WAV_FILE_AT_ALL_JUST_RANDOM_BYTES_WITH_EXTRA_PADDING_HERE")
        self.assertFalse(passed)
        self.assertIn("Malformed WAV header", reason)

    def test_04_near_silent_audio_rejected(self):
        silent_wav = _make_test_wav(duration_sec=1.0, amplitude=0.0001)
        passed, reason, _ = self.guard.preflight_check(silent_wav)
        self.assertFalse(passed)
        self.assertIn("Near-silent", reason)

    def test_05_clipped_audio_rejected(self):
        # Generate heavy clipping with 100% full scale square wave
        duration_sec = 1.0
        sample_rate = 16000
        num_samples = int(sample_rate * duration_sec)
        sig = np.full(num_samples, 32767, dtype=np.int16)
        bio = io.BytesIO()
        with wave.open(bio, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(sig.tobytes())
        clipped_wav = bio.getvalue()

        passed, reason, _ = self.guard.preflight_check(clipped_wav)
        self.assertFalse(passed)
        self.assertIn("clipping", reason.lower())

    def test_06_very_short_audio_rejected(self):
        short_wav = _make_test_wav(duration_sec=0.1, amplitude=0.5)
        passed, reason, _ = self.guard.preflight_check(short_wav)
        self.assertFalse(passed)
        self.assertIn("too short", reason.lower())

    def test_07_very_long_audio_rejected(self):
        guard = ZyeAudioClarityGuard(ClarityConfig(max_duration_seconds=5.0))
        long_wav = _make_test_wav(duration_sec=6.0, amplitude=0.5)
        passed, reason, _ = guard.preflight_check(long_wav)
        self.assertFalse(passed)
        self.assertIn("exceeds maximum", reason.lower())

    def test_08_clear_assessment(self):
        assessment = self.guard.assess_audio(self.valid_wav)
        self.assertTrue(assessment.is_clear)
        self.assertEqual(assessment.clarity, "clear")
        self.assertFalse(assessment.needs_clarification)

    def test_09_gemini_assessment_unclear_flagged(self):
        ai_eval = {"clarity": "unclear", "reason": "Speech muffled by traffic", "needs_clarification": True}
        assessment = self.guard.assess_audio(self.valid_wav, gemini_assessment=ai_eval)
        self.assertFalse(assessment.is_clear)
        self.assertEqual(assessment.clarity, "unclear")
        self.assertTrue(assessment.needs_clarification)

    def test_10_gemini_assessment_incomplete_flagged(self):
        ai_eval = {"clarity": "incomplete", "reason": "Sentence cut off mid-word", "needs_clarification": True}
        assessment = self.guard.assess_audio(self.valid_wav, gemini_assessment=ai_eval)
        self.assertFalse(assessment.is_clear)
        self.assertEqual(assessment.clarity, "incomplete")

    def test_11_gemini_assessment_ambiguous_flagged(self):
        ai_eval = {"clarity": "ambiguous", "reason": "Could mean two conflicting commands", "needs_clarification": True}
        assessment = self.guard.assess_audio(self.valid_wav, gemini_assessment=ai_eval)
        self.assertFalse(assessment.is_clear)
        self.assertEqual(assessment.clarity, "ambiguous")

    def test_12_tool_execution_prohibited_when_unclear(self):
        unclear_assessment = ClarityAssessment(
            is_clear=False,
            clarity="unclear",
            reason="Noise",
            needs_clarification=True,
            preflight_passed=True,
            details={},
        )
        can_exec = self.guard.can_execute_tools(unclear_assessment, is_text_mode=False)
        self.assertFalse(can_exec)

    def test_13_tool_execution_permitted_when_clear(self):
        clear_assessment = ClarityAssessment(
            is_clear=True,
            clarity="clear",
            reason="Good",
            needs_clarification=False,
            preflight_passed=True,
            details={},
        )
        can_exec = self.guard.can_execute_tools(clear_assessment, is_text_mode=False)
        self.assertTrue(can_exec)

    def test_14_text_mode_bypasses_audio_clarity_check(self):
        unclear_assessment = ClarityAssessment(
            is_clear=False,
            clarity="unclear",
            reason="Bad mic",
            needs_clarification=True,
            preflight_passed=False,
            details={},
        )
        # In text mode (Alt+Z), tools CAN be executed regardless of mic clarity
        can_exec = self.guard.can_execute_tools(unclear_assessment, is_text_mode=True)
        self.assertTrue(can_exec)

    def test_15_exact_tanglish_clarification_message(self):
        msg = self.guard.get_clarification_response()
        self.assertEqual(msg, "Konjam clear-ah kekkala, thirumba solreengala?")
        self.assertEqual(EXACT_CLARIFICATION_MESSAGE, "Konjam clear-ah kekkala, thirumba solreengala?")

    def test_16_get_status_telemetry(self):
        status = self.guard.get_status()
        self.assertIn("enabled", status)
        self.assertIn("strict_mode", status)
        self.assertIn("block_tools_when_unclear", status)
        self.assertIn("clarification_message", status)


if __name__ == "__main__":
    unittest.main(verbosity=2)
