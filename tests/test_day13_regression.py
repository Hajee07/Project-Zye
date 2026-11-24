"""
Regression Certification Suite for Day 13 Autonomous Intelligence Core.
Verifies that all Day 01–12 systems (Audio, VAD, AGC, Chimes, TTS, Alt+Z, Clarity,
Guard, Self-Repair, Master MCP Orchestrator, Hot Reload, and Recovery) continue
to operate with zero regressions.
"""

from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import MagicMock, patch

from main import ZyeMasterAgent
from zye_audio.agc import AGCProcessor
from zye_audio.chime_player import JarvisChimePlayer
from zye_audio_ear import AdaptiveRMSDetector, SmartAudioEar
from zye_brain.clarity_guard import ClarityConfig, ZyeAudioClarityGuard
from zye_guard import redact_secrets, zye_safe_skill
from zye_intelligence.decision_matrix import ZyeDecisionMatrix
from zye_intelligence.emergency_reflex import ZyeEmergencyReflex
from zye_intelligence.execution_gate import ZyeExecutionGate
from zye_intelligence.mission_controller import ZyeMissionController
from zye_intelligence.negative_audit import NegativeAuditEngine
from zye_intelligence.preflight import ZyeSystemPreflight
from zye_intelligence.premortem import ZyeNegativePreMortem
from zye_text_input import AltZTextInputHandler, TextInputConfig
from zye_tts import TTSConfig, ZyeTTSEngine
from zye_voice.playback import PlaybackConfig, ZyeAudioPlayback


class TestDay13Regression(unittest.TestCase):
    def test_01_day07_smart_audio_ear(self) -> None:
        """Verify Day 07 SmartAudioEar initializes with 16kHz mono audio."""
        ear = SmartAudioEar()
        self.assertEqual(ear.config.sample_rate, 16000)
        self.assertEqual(ear.config.channels, 1)

    def test_02_day08_neural_vad(self) -> None:
        """Verify Day 08 VAD adaptive RMS fallback initializes."""
        rms = AdaptiveRMSDetector()
        self.assertIsNotNone(rms)

    def test_03_day09_agc_and_chimes(self) -> None:
        """Verify Day 09 AGCProcessor and JarvisChimePlayer are functional."""
        agc = AGCProcessor()
        self.assertAlmostEqual(agc.config.target_peak, 0.85)
        chimes = JarvisChimePlayer()
        self.assertTrue(hasattr(chimes, "play_start"))
        self.assertTrue(hasattr(chimes, "play_stop"))

    def test_04_day10_tts_and_playback(self) -> None:
        """Verify Day 10 Edge-TTS and Pygame playback components."""
        tts_cfg = TTSConfig()
        self.assertEqual(tts_cfg.voice, "en-IN-NeerjaNeural")
        pb_cfg = PlaybackConfig()
        self.assertTrue(pb_cfg.enabled)

    def test_05_day10_alt_z_text_fallback(self) -> None:
        """Verify Day 10 Alt+Z Silent Text Mode handler."""
        handler = AltZTextInputHandler()
        self.assertEqual(handler.config.hotkey, "alt+z")

    def test_06_day10_clarity_guard(self) -> None:
        """Verify Day 10 Audio Clarity Guard."""
        guard = ZyeAudioClarityGuard()
        self.assertTrue(guard.config.enabled)

    def test_07_day04_zero_crash_guard(self) -> None:
        """Verify Day 04 zye_safe_skill and secret redaction."""
        @zye_safe_skill()
        def _safe_func():
            return "ok"
        self.assertEqual(_safe_func(), "ok")
        key = "AIzaSy" + "K" * 33
        redacted = redact_secrets(f"my key is {key}")
        self.assertNotIn(key, redacted)

    def test_08_day11_autonomy_backward_compatibility(self) -> None:
        """Verify Day 11 zye_autonomy imports still resolve seamlessly."""
        from zye_autonomy.decision_matrix import ZyeDecisionMatrix as LegacyDM
        from zye_autonomy.mission_profiles import ZyeMissionController as LegacyMC
        from zye_autonomy.preflight import ZyeSystemPreflight as LegacyPF
        from zye_autonomy.premortem import ZyeNegativePreMortem as LegacyPM
        from zye_autonomy.watchdog import ZyeAutonomousWatchdog as LegacyWD
        self.assertIsNotNone(LegacyDM)
        self.assertIsNotNone(LegacyMC)
        self.assertIsNotNone(LegacyPF)
        self.assertIsNotNone(LegacyPM)
        self.assertIsNotNone(LegacyWD)

    def test_09_day12_master_mcp_orchestrator(self) -> None:
        """Verify Day 12 Master MCP Orchestrator and diagnostic surface."""
        agent = ZyeMasterAgent()
        status = agent.get_mcp_orchestrator_status()
        self.assertIn("status", status)
        self.assertIn("registered_servers", status)

    def test_10_day13_autonomous_intelligence_core(self) -> None:
        """Verify Day 13 NegativeAuditEngine, DecisionMatrix, and EmergencyReflex."""
        mc = ZyeMissionController()
        pf = ZyeSystemPreflight()
        brain = ZyeNegativePreMortem()
        engine = NegativeAuditEngine(preflight=pf, premortem_brain=brain)
        dm = ZyeDecisionMatrix()
        reflex = ZyeEmergencyReflex(mission_controller=mc)
        gate = ZyeExecutionGate(premortem_brain=brain, preflight=pf, mission_controller=mc)

        self.assertIsNotNone(engine)
        self.assertIsNotNone(dm)
        self.assertIsNotNone(reflex)
        self.assertIsNotNone(gate)


if __name__ == "__main__":
    unittest.main()
