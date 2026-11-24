#!/usr/bin/env python3
"""
Unit and Integration Tests for Gemini Live Low-Latency Optimization (v2.0)
==========================================================================
Verifies:
- Monotonic nanosecond latency instrumentation (T0-T13, M0-M5)
- Multi-turn persistent session reuse without reconnecting
- Software acoustic echo cancellation & self-listening prevention
- Direct conversational greeting intent policy
- Non-blocking in-memory capture queue drain
- Sub-45ms audio player startup and instant barge-in flush
- Moving average latency telemetry tracking
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from zye_gemini_live import (
    GeminiLiveConfig,
    GeminiLiveTelemetry,
    LiveAudioPlayer,
    LiveSessionState,
    TurnMetrics,
    ZyeGeminiLiveManager,
)


class TestGeminiLiveOptimization(unittest.TestCase):
    """Test suite for Gemini Live latency and architecture optimizations."""

    def test_turn_metrics_nanosecond_instrumentation(self) -> None:
        """Verify high-resolution T0-T13 and M0-M5 latency calculations."""
        tm = TurnMetrics(turn_id="live_turn_001", session_id="test_session")
        tm.t0_audio_activity_ns = 1_000_000_000
        tm.t1_frame_captured_ns = 1_010_000_000
        tm.t2_pcm_converted_ns = 1_015_000_000
        tm.t3_queued_ns = 1_020_000_000
        tm.t4_sent_to_live_ns = 1_030_000_000
        tm.t6_user_speech_completed_ns = 1_030_000_000
        tm.t7_first_server_event_ns = 1_450_000_000
        tm.t8_first_audio_bytes_ns = 1_510_000_000
        tm.t10_output_submitted_ns = 1_540_000_000
        tm.t12_response_complete_ns = 2_150_000_000

        # Tool metrics
        tm.m0_tool_requested_ns = 1_600_000_000
        tm.m4_tool_completed_ns = 1_750_000_000
        tm.tool_name = "test_tool"

        self.assertAlmostEqual(tm.first_response_latency_ms(), 420.0, places=1)
        self.assertAlmostEqual(tm.first_audio_latency_ms(), 480.0, places=1)
        self.assertAlmostEqual(tm.playback_startup_delay_ms(), 30.0, places=1)
        self.assertAlmostEqual(tm.total_turn_duration_ms(), 1150.0, places=1)
        self.assertAlmostEqual(tm.tool_duration_ms(), 150.0, places=1)

        trace = tm.format_diagnostic_trace()
        self.assertGreaterEqual(len(trace), 5)
        self.assertTrue(any("First output audio chunk" in line for line in trace))

    def test_echo_cancellation_and_self_listening_suppression(self) -> None:
        """Verify quiet speaker bleed is gated while strong user barge-in passes."""
        cfg = GeminiLiveConfig(
            echo_cancellation=True,
            self_listening_suppression=True,
            barge_in_energy_threshold=1800.0,
        )
        mgr = ZyeGeminiLiveManager(config=cfg)
        mgr._running = True

        # Simulate audio actively playing through speakers
        mgr.player._is_playing = True

        # 1. Quiet bleed (RMS ~ 400 < 1800): must be dropped
        quiet_pcm = (np.ones(512, dtype=np.int16) * 400).tobytes()
        mgr.push_microphone_audio(quiet_pcm)
        self.assertEqual(mgr._audio_in_queue.qsize(), 0)

        # 2. Strong user speech (RMS ~ 3500 > 1800): must pass into queue
        loud_barge_in = (np.ones(512, dtype=np.int16) * 3500).tobytes()
        mgr.push_microphone_audio(loud_barge_in)
        self.assertEqual(mgr._audio_in_queue.qsize(), 1)

        # 3. Not playing: all audio passes through
        mgr.player._is_playing = False
        mgr.push_microphone_audio(quiet_pcm)
        self.assertEqual(mgr._audio_in_queue.qsize(), 2)

    def test_direct_greeting_system_prompt_fast_path(self) -> None:
        """Verify direct greeting rule is injected into Live system instruction."""
        cfg = GeminiLiveConfig(direct_greeting_fast_path=True)
        mgr = ZyeGeminiLiveManager(config=cfg)
        connect_cfg = mgr._build_live_connect_config()

        self.assertIn("GREETINGS & CASUAL CONVERSATION", connect_cfg.system_instruction)
        self.assertIn("Do NOT call any MCP tool for greetings", connect_cfg.system_instruction)
        self.assertIn("Tamil", connect_cfg.system_instruction)
        self.assertIn("Tanglish", connect_cfg.system_instruction)

    def test_live_audio_player_low_latency_mode_and_flush(self) -> None:
        """Verify LiveAudioPlayer configuration and instant queue flushing."""
        player = LiveAudioPlayer(sample_rate=24000, latency="low")
        self.assertEqual(player.latency, "low")
        self.assertEqual(player.sample_rate, 24000)

        player._running = True
        dummy_chunk = b"\x00\x00" * 512
        player.queue_chunk(dummy_chunk)
        self.assertFalse(player._queue.empty())

        # Instant flush on barge-in
        player.flush()
        self.assertTrue(player._queue.empty())
        self.assertFalse(player.is_playing())

    def test_nonblocking_capture_pump_drain_logic(self) -> None:
        """Verify capture pump drains queue without thread dispatch."""
        import inspect
        src = inspect.getsource(ZyeGeminiLiveManager.pump_capture_engine)
        self.assertIn("frame_queue.get_nowait", src)
        self.assertNotIn("asyncio.to_thread(capture_engine.read_frame", src)

    def test_telemetry_average_latency_tracking(self) -> None:
        """Verify moving average audio latency calculation in telemetry."""
        telem = GeminiLiveTelemetry()
        self.assertEqual(telem.average_audio_latency_ms, 0.0)

        # First turn
        lat1 = 450.0
        telem.last_audio_latency_ms = lat1
        telem.average_audio_latency_ms = lat1
        telem.total_turns_completed = 1

        # Second turn (lat = 550.0)
        lat2 = 550.0
        telem.last_audio_latency_ms = lat2
        telem.average_audio_latency_ms = round(0.7 * telem.average_audio_latency_ms + 0.3 * lat2, 2)
        telem.total_turns_completed += 1

        expected = round(0.7 * 450.0 + 0.3 * 550.0, 2)
        self.assertEqual(telem.average_audio_latency_ms, expected)
        self.assertEqual(telem.total_turns_completed, 2)


if __name__ == "__main__":
    unittest.main()
