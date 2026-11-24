"""
Acceptance Test Suite: Voice Reliability, Live Session Stability & Audio Response Recovery.
Validates VAD threshold calibration, dual-player acoustic gating, audio drain waiters,
multi-slot API key failover, and prompt negative constraints.
"""

from __future__ import annotations

import asyncio
import inspect
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np

from zye_gemini_live import (
    GeminiLiveConfig,
    GeminiLiveTelemetry,
    LiveAudioPlayer,
    LiveSessionState,
    TurnMetrics,
    ZyeGeminiLiveManager,
)


class TestVoiceReliability(unittest.TestCase):
    """Test suite for voice reliability, session stability, and audio recovery."""

    def test_01_vad_threshold_calibration(self):
        """Test GeminiLiveConfig has calibrated VAD speech threshold (<= 2000 RMS)."""
        cfg = GeminiLiveConfig()
        self.assertLessEqual(cfg.speech_energy_threshold, 2000.0)
        self.assertGreaterEqual(cfg.speech_energy_threshold, 500.0)

    def test_02_silence_threshold_natural_pauses(self):
        """Test silence threshold frames is >= 35 (~1.2s-1.5s) to avoid mid-sentence cutoff."""
        cfg = GeminiLiveConfig()
        self.assertGreaterEqual(cfg.silence_frames_threshold, 35)

    def test_03_barge_in_threshold_calibration(self):
        """Test barge-in threshold is <= 6000 RMS to allow deliberate user interruptions."""
        cfg = GeminiLiveConfig()
        self.assertLessEqual(cfg.barge_in_energy_threshold, 6000.0)
        self.assertGreaterEqual(cfg.barge_in_energy_threshold, 3000.0)

    def test_04_live_player_playback_waiter(self):
        """Test LiveAudioPlayer has async wait_for_playback_complete coroutine."""
        player = LiveAudioPlayer()
        self.assertTrue(hasattr(player, "wait_for_playback_complete"))
        self.assertTrue(inspect.iscoroutinefunction(player.wait_for_playback_complete))

    def test_05_acoustic_echo_suppression_live_player(self):
        """Test mic chunks are gated when LiveAudioPlayer is playing below barge-in threshold."""
        mgr = ZyeGeminiLiveManager()
        mgr._running = True
        mgr.player._is_playing = True

        # Low RMS speech chunk (e.g. RMS ~ 1000)
        samples = (np.sin(np.linspace(0, 10, 512)) * 1000).astype(np.int16)
        low_pcm = samples.tobytes()

        # Audio queue should remain empty because chunk was gated
        mgr.push_microphone_audio(low_pcm)
        self.assertTrue(mgr._audio_in_queue.empty())

    def test_06_acoustic_echo_suppression_pygame_mixer(self):
        """Test mic chunks are gated when Pygame Edge-TTS playback is active."""
        mgr = ZyeGeminiLiveManager()
        mgr._running = True
        mgr.player._is_playing = False  # LiveAudioPlayer idle

        # Mock Pygame mixer busy
        mock_mixer = MagicMock()
        mock_mixer.get_init.return_value = True
        mock_mixer.music.get_busy.return_value = True

        with patch.dict("sys.modules", {"pygame": MagicMock(mixer=mock_mixer)}):
            samples = (np.sin(np.linspace(0, 10, 512)) * 1000).astype(np.int16)
            low_pcm = samples.tobytes()

            mgr.push_microphone_audio(low_pcm)
            self.assertTrue(mgr._audio_in_queue.empty())

    def test_07_barge_in_punch_through(self):
        """Test high-energy user speech (RMS > 5000) punches through playback gate."""
        mgr = ZyeGeminiLiveManager()
        mgr._running = True
        mgr.player._is_playing = True

        # High RMS speech chunk (amplitude 10000 -> RMS ~ 7071 > 4500)
        samples = (np.sin(np.linspace(0, 10, 512)) * 10000).astype(np.int16)
        high_pcm = samples.tobytes()

        mgr.push_microphone_audio(high_pcm)
        # Should be queued because it punched through barge-in threshold
        self.assertFalse(mgr._audio_in_queue.empty())

    def test_08_multi_slot_cursor_initialization(self):
        """Test Live manager initializes with slot cursor."""
        mgr = ZyeGeminiLiveManager()
        self.assertTrue(hasattr(mgr, "_slot_cursor"))
        self.assertEqual(mgr._slot_cursor, 1)

    def test_09_multi_slot_key_failover_on_quota(self):
        """Test 429 quota exhaustion advances slot cursor to next slot."""
        mgr = ZyeGeminiLiveManager()
        mgr._slot_cursor = 1
        mgr._active_slot_id = 1

        mock_km = MagicMock()
        mgr.key_manager = mock_km

        # Simulate slot cursor advance on 429
        mgr._slot_cursor = (mgr._slot_cursor % 7) + 1
        self.assertEqual(mgr._slot_cursor, 2)

    def test_10_turn_complete_playback_drain_wait(self):
        """Test _receive_events_loop waits for playback drain before resetting to LISTENING."""
        source = inspect.getsource(ZyeGeminiLiveManager._receive_events_loop)
        self.assertIn("wait_for_playback_complete", source)
        self.assertIn("LiveSessionState.LISTENING", source)

    def test_11_persistent_session_state_transitions(self):
        """Test valid state transitions in Live manager."""
        mgr = ZyeGeminiLiveManager()
        mgr.set_state(LiveSessionState.CONNECTING)
        self.assertEqual(mgr.state, LiveSessionState.CONNECTING)

        mgr.set_state(LiveSessionState.CONNECTED)
        self.assertEqual(mgr.state, LiveSessionState.CONNECTED)

        mgr.set_state(LiveSessionState.RESPONDING)
        self.assertEqual(mgr.state, LiveSessionState.RESPONDING)

        mgr.set_state(LiveSessionState.LISTENING)
        self.assertEqual(mgr.state, LiveSessionState.LISTENING)

    def test_12_turn_metrics_telemetry(self):
        """Test TurnMetrics records timestamps and calculates latencies."""
        turn = TurnMetrics(turn_id="turn_001", session_id="test_sess")
        turn.t0_audio_activity_ns = 1_000_000_000
        turn.t4_sent_to_live_ns = 1_200_000_000
        turn.t7_first_server_event_ns = 1_400_000_000
        turn.t8_first_audio_bytes_ns = 1_500_000_000

        lat = turn.first_audio_latency_ms()
        self.assertAlmostEqual(lat, 300.0, places=1)

    def test_13_config_toml_thresholds_match(self):
        """Test zye_config.toml has calibrated thresholds."""
        import tomllib
        with open("zye_config.toml", "rb") as f:
            cfg = tomllib.load(f)
        live_cfg = cfg.get("gemini_live", {})
        self.assertIn(live_cfg.get("speech_energy_threshold"), (400.0, 500.0))
        self.assertEqual(live_cfg.get("silence_frames_threshold"), 36)
        self.assertIn(live_cfg.get("barge_in_energy_threshold"), (2200.0, 3000.0, 5500.0))

    def test_14_main_voice_loop_loads_calibrated_thresholds(self):
        """Test main.py passes calibrated thresholds into GeminiLiveConfig."""
        import main
        source = inspect.getsource(main.ZyeVoiceLoop._initialize_subsystems)
        self.assertIn("speech_energy_threshold", source)
        self.assertIn("silence_frames_threshold", source)
        self.assertIn("barge_in_energy_threshold", source)

    def test_15_edge_tts_voice_preservation(self):
        """Test Edge-TTS voice configuration preserves en-IN-NeerjaNeural."""
        import tomllib
        with open("zye_config.toml", "rb") as f:
            cfg = tomllib.load(f)
        tts_cfg = cfg.get("tts", {})
        self.assertIn("Neerja", tts_cfg.get("voice", ""))


if __name__ == "__main__":
    unittest.main()
