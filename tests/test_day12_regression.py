#!/usr/bin/env python3
"""
ZYE AI — Day 12 Cross-System Full Regression Test Suite
======================================================
Verifies that all components from Day 01 through Day 12 remain intact,
operational, and non-conflicting.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestDay12Regression(unittest.TestCase):
    """Regression suite verifying zero regressions across Day 01–12."""

    def test_01_day01_foundation(self) -> None:
        """Project root and virtual environment are valid."""
        self.assertTrue(PROJECT_ROOT.exists())
        self.assertTrue((PROJECT_ROOT / "zye_config.toml").is_file())

    def test_02_day04_guard(self) -> None:
        """ZyeGuard circuit breaker and secret redaction work."""
        from zye_guard import redact_secrets, zye_safe_skill
        key = "AIzaSy" + "A" * 33
        self.assertNotIn(key, redact_secrets(f"key is {key}"))

        @zye_safe_skill()
        def _safe_func():
            return 42

        self.assertEqual(_safe_func(), 42)

    def test_03_day05_self_repair(self) -> None:
        """Self repair tools are importable and functional."""
        import self_repair_mcp
        self.assertTrue(hasattr(self_repair_mcp, "read_recent_error_logs"))
        self.assertTrue(hasattr(self_repair_mcp, "read_own_source_code"))

    def test_04_day06_code_repair(self) -> None:
        """Code repair patch and rollback engines are available."""
        import self_repair_mcp
        self.assertTrue(hasattr(self_repair_mcp, "preview_code_patch"))
        self.assertTrue(hasattr(self_repair_mcp, "patch_own_code"))
        self.assertTrue(hasattr(self_repair_mcp, "rollback_code_backup"))

    def test_05_day07_audio_ear(self) -> None:
        """SmartAudioEar is importable with standard audio configuration."""
        from zye_audio_ear import AudioConfig, SmartAudioEar
        cfg = AudioConfig()
        self.assertEqual(cfg.sample_rate, 16000)
        self.assertEqual(cfg.pre_roll_seconds, 0.64)

    def test_06_day08_neural_vad(self) -> None:
        """Silero Neural VAD engine and fallback RMS are preserved."""
        from zye_audio_ear import AdaptiveRMSDetector, SmartAudioEar
        ear = SmartAudioEar()
        self.assertEqual(ear.config.sample_rate, 16000)
        rms = AdaptiveRMSDetector()
        self.assertIsNotNone(rms)

    def test_07_day09_agc_and_chimes(self) -> None:
        """AGC processor and synthesized Jarvis chimes are operational."""
        from zye_audio.agc import AGCProcessor
        from zye_audio.chime_player import JarvisChimePlayer
        agc = AGCProcessor()
        self.assertEqual(agc.config.target_peak, 0.85)
        chimes = JarvisChimePlayer()
        self.assertTrue(hasattr(chimes, "play_start"))
        self.assertTrue(hasattr(chimes, "play_stop"))

    def test_08_day10_voice_interaction(self) -> None:
        """Edge-TTS, Pygame playback, hotkey, and Clarity Guard intact."""
        from zye_brain.clarity_guard import ZyeAudioClarityGuard
        from zye_input.hotkey_controller import ZyeHotkeyController
        from zye_voice.edge_tts_engine import ZyeEdgeTTSEngine
        from zye_voice.playback import ZyeAudioPlayback

        guard = ZyeAudioClarityGuard()
        self.assertTrue(guard.config.strict_mode)
        hk = ZyeHotkeyController()
        self.assertEqual(hk.config.shortcut, "alt+z")

    def test_09_day11_autonomous_intelligence(self) -> None:
        """Dual-Brain premortem, decision matrix, missions, and watchdog intact."""
        from zye_autonomy.decision_matrix import PRIORITY_WEIGHTS, ZyeDecisionMatrix
        from zye_autonomy.emergency_reflex import ZyeEmergencyReflex
        from zye_autonomy.execution_gate import ZyeExecutionGate
        from zye_autonomy.mission_profiles import ZyeMissionController
        from zye_autonomy.preflight import ZyeSystemPreflight
        from zye_autonomy.premortem import ZyeNegativePreMortem
        from zye_autonomy.watchdog import ZyeAutonomousWatchdog

        mc = ZyeMissionController()
        self.assertTrue(mc.validate_mission("NORMAL_ASSISTANT"))
        dm = ZyeDecisionMatrix()
        self.assertIn("balanced", PRIORITY_WEIGHTS)
        pf = ZyeSystemPreflight()
        self.assertTrue(hasattr(pf, "collect_system_metrics"))

    def test_10_day12_master_orchestrator(self) -> None:
        """Master orchestrator modules and agent are fully integrated."""
        from main import ZyeMasterAgent
        from zye_orchestrator import (
            HotReloadController,
            MCPConnectionManager,
            MCPRecoveryController,
            MCPServerHealthMonitor,
            ServerRegistry,
            ZyeMCPExecutionRouter,
            ZyeToolRegistry,
        )
        agent = ZyeMasterAgent(root=PROJECT_ROOT)
        self.assertIsInstance(agent.registry, ServerRegistry)
        self.assertIsInstance(agent.tool_registry, ZyeToolRegistry)
        self.assertIsInstance(agent.conn_mgr, MCPConnectionManager)
        self.assertIsInstance(agent.hot_reload_ctrl, HotReloadController)
        self.assertIsInstance(agent.recovery_ctrl, MCPRecoveryController)
        self.assertIsInstance(agent.execution_router, ZyeMCPExecutionRouter)
        self.assertIsInstance(agent.health_monitor, MCPServerHealthMonitor)


if __name__ == "__main__":
    unittest.main()
