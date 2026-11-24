#!/usr/bin/env python3
"""
ZYE AI — Day 10 TTS Engine Test Suite
======================================
Tests for zye_tts.py: TTSConfig, TTSResult, ZyeTTSEngine.
All network calls are mocked — CI-safe.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import time
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zye_tts import (
    TTSConfig,
    TTSConfigError,
    TTSError,
    TTSPlaybackError,
    TTSResult,
    TTSSynthesisError,
    TTSUnavailableError,
    ZyeTTSEngine,
    get_default_engine,
    speak,
)


# ---------------------------------------------------------------------------
# TTSConfig Tests
# ---------------------------------------------------------------------------

class TestTTSConfig(unittest.TestCase):
    """Tests for TTSConfig dataclass validation."""

    def test_01_default_voice_is_neerja(self):
        cfg = TTSConfig()
        self.assertEqual(cfg.voice, "en-IN-NeerjaNeural")

    def test_02_default_rate_is_zero(self):
        cfg = TTSConfig()
        self.assertEqual(cfg.rate, "+0%")

    def test_03_default_volume_is_zero(self):
        cfg = TTSConfig()
        self.assertEqual(cfg.volume, "+0%")

    def test_04_default_pitch_is_zero(self):
        cfg = TTSConfig()
        self.assertEqual(cfg.pitch, "+0Hz")

    def test_05_default_timeout_is_15(self):
        cfg = TTSConfig()
        self.assertEqual(cfg.timeout_seconds, 15.0)

    def test_06_default_playback_enabled(self):
        cfg = TTSConfig()
        self.assertTrue(cfg.playback_enabled)

    def test_07_default_playback_volume_is_1(self):
        cfg = TTSConfig()
        self.assertEqual(cfg.playback_volume, 1.0)

    def test_08_empty_voice_raises(self):
        with self.assertRaises(TTSConfigError):
            TTSConfig(voice="")

    def test_09_zero_timeout_raises(self):
        with self.assertRaises(TTSConfigError):
            TTSConfig(timeout_seconds=0.0)

    def test_10_negative_timeout_raises(self):
        with self.assertRaises(TTSConfigError):
            TTSConfig(timeout_seconds=-1.0)

    def test_11_playback_volume_above_2_raises(self):
        with self.assertRaises(TTSConfigError):
            TTSConfig(playback_volume=2.1)

    def test_12_playback_volume_negative_raises(self):
        with self.assertRaises(TTSConfigError):
            TTSConfig(playback_volume=-0.1)

    def test_13_valid_custom_voice(self):
        cfg = TTSConfig(voice="en-US-AriaNeural")
        self.assertEqual(cfg.voice, "en-US-AriaNeural")

    def test_14_valid_playback_volume_zero(self):
        cfg = TTSConfig(playback_volume=0.0)
        self.assertEqual(cfg.playback_volume, 0.0)

    def test_15_valid_playback_volume_max(self):
        cfg = TTSConfig(playback_volume=2.0)
        self.assertEqual(cfg.playback_volume, 2.0)


# ---------------------------------------------------------------------------
# TTSResult Tests
# ---------------------------------------------------------------------------

class TestTTSResult(unittest.TestCase):
    """Tests for TTSResult dataclass."""

    def test_16_success_result_fields(self):
        r = TTSResult(
            text="hello",
            audio_bytes=b"\x00\x01",
            voice="en-IN-NeerjaNeural",
            synthesis_duration_ms=120.0,
            byte_count=2,
            status="SUCCESS",
        )
        self.assertEqual(r.text, "hello")
        self.assertEqual(r.audio_bytes, b"\x00\x01")
        self.assertEqual(r.byte_count, 2)
        self.assertEqual(r.status, "SUCCESS")
        self.assertIsNone(r.error)

    def test_17_failed_result_has_error(self):
        r = TTSResult(
            text="hi",
            audio_bytes=b"",
            voice="en-IN-NeerjaNeural",
            synthesis_duration_ms=5.0,
            byte_count=0,
            status="FAILED",
            error="network error",
        )
        self.assertEqual(r.error, "network error")
        self.assertEqual(r.status, "FAILED")

    def test_18_empty_result_zero_bytes(self):
        r = TTSResult(
            text="",
            audio_bytes=b"",
            voice="en-IN-NeerjaNeural",
            synthesis_duration_ms=0.0,
            byte_count=0,
            status="EMPTY",
        )
        self.assertEqual(r.byte_count, 0)
        self.assertEqual(r.status, "EMPTY")

    def test_19_unavailable_result(self):
        r = TTSResult(
            text="test",
            audio_bytes=b"",
            voice="en-IN-NeerjaNeural",
            synthesis_duration_ms=0.0,
            byte_count=0,
            status="UNAVAILABLE",
            error="edge-tts library is not installed",
        )
        self.assertEqual(r.status, "UNAVAILABLE")


# ---------------------------------------------------------------------------
# ZyeTTSEngine Init Tests
# ---------------------------------------------------------------------------

class TestZyeTTSEngineInit(unittest.TestCase):
    """Tests for ZyeTTSEngine instantiation and diagnostics."""

    def test_20_engine_instantiates_with_defaults(self):
        engine = ZyeTTSEngine()
        self.assertIsNotNone(engine)

    def test_21_engine_uses_provided_config(self):
        cfg = TTSConfig(voice="en-US-AriaNeural")
        engine = ZyeTTSEngine(cfg)
        self.assertEqual(engine.config.voice, "en-US-AriaNeural")

    def test_22_initial_counters_zero(self):
        engine = ZyeTTSEngine()
        self.assertEqual(engine.total_synthesized, 0)
        self.assertEqual(engine.total_errors, 0)

    def test_23_diagnostics_has_required_keys(self):
        engine = ZyeTTSEngine()
        diag = engine.get_diagnostics()
        required = [
            "status", "edge_tts_available", "edge_tts_version",
            "configured_voice", "rate", "volume", "pitch",
            "timeout_seconds", "playback_enabled",
            "total_synthesized", "total_errors",
            "last_synthesis_ms", "last_voice_used",
        ]
        for key in required:
            self.assertIn(key, diag, f"Missing diagnostics key: {key}")

    def test_24_diagnostics_status_is_ready_or_unavailable(self):
        engine = ZyeTTSEngine()
        diag = engine.get_diagnostics()
        self.assertIn(diag["status"], ("ready", "unavailable"))

    def test_25_diagnostics_configured_voice(self):
        cfg = TTSConfig(voice="en-GB-SoniaNeural")
        engine = ZyeTTSEngine(cfg)
        self.assertEqual(engine.get_diagnostics()["configured_voice"], "en-GB-SoniaNeural")


# ---------------------------------------------------------------------------
# ZyeTTSEngine Synthesis Tests (mocked edge-tts)
# ---------------------------------------------------------------------------

FAKE_MP3 = b"\xff\xfb\x90\x00" * 100  # fake MP3 header bytes


def _make_mock_communicate(audio_bytes: bytes = FAKE_MP3):
    """Build a mock Communicate object whose .stream() yields audio chunks."""
    async def _mock_stream():
        yield {"type": "audio", "data": audio_bytes}
    mock_comm = MagicMock()
    mock_comm.stream = _mock_stream
    return mock_comm


class TestZyeTTSEngineSynthesis(unittest.TestCase):
    """Tests for ZyeTTSEngine.synthesize() with mocked edge-tts."""

    def setUp(self):
        self.engine = ZyeTTSEngine(TTSConfig(timeout_seconds=5.0))

    def _run(self, coro):
        return asyncio.run(coro)

    def test_26_empty_text_returns_empty_status(self):
        result = self._run(self.engine.synthesize(""))
        self.assertEqual(result.status, "EMPTY")
        self.assertEqual(result.byte_count, 0)

    def test_27_whitespace_only_returns_empty(self):
        result = self._run(self.engine.synthesize("   "))
        self.assertEqual(result.status, "EMPTY")

    def test_28_unavailable_engine_returns_unavailable(self):
        engine = ZyeTTSEngine()
        engine._available = False
        result = self._run(engine.synthesize("hello world"))
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(engine.total_errors, 1)

    def test_29_success_with_mocked_communicate(self):
        engine = ZyeTTSEngine()
        engine._available = True

        mock_comm = _make_mock_communicate(FAKE_MP3)

        with patch("zye_tts.Communicate", return_value=mock_comm):
            result = self._run(engine.synthesize("Hello Zye"))

        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(result.audio_bytes, FAKE_MP3)
        self.assertEqual(result.byte_count, len(FAKE_MP3))
        self.assertEqual(engine.total_synthesized, 1)

    def test_30_synthesis_records_timing(self):
        engine = ZyeTTSEngine()
        engine._available = True

        mock_comm = _make_mock_communicate(FAKE_MP3)
        with patch("zye_tts.Communicate", return_value=mock_comm):
            result = self._run(engine.synthesize("test"))

        self.assertGreaterEqual(result.synthesis_duration_ms, 0.0)
        self.assertEqual(engine.last_synthesis_ms, result.synthesis_duration_ms)

    def test_31_synthesis_records_voice_used(self):
        engine = ZyeTTSEngine()
        engine._available = True

        mock_comm = _make_mock_communicate(FAKE_MP3)
        with patch("zye_tts.Communicate", return_value=mock_comm):
            self._run(engine.synthesize("test", voice="en-US-AriaNeural"))

        self.assertEqual(engine.last_voice_used, "en-US-AriaNeural")

    def test_32_timeout_returns_failed(self):
        engine = ZyeTTSEngine(TTSConfig(timeout_seconds=0.001))
        engine._available = True

        async def _slow_stream():
            await asyncio.sleep(5)
            yield {"type": "audio", "data": FAKE_MP3}  # never reached

        mock_comm = MagicMock()
        mock_comm.stream = _slow_stream

        with patch("zye_tts.Communicate", return_value=mock_comm):
            result = self._run(engine.synthesize("test"))

        self.assertEqual(result.status, "FAILED")
        self.assertIn("timed out", result.error or "")
        self.assertEqual(engine.total_errors, 1)

    def test_33_exception_in_stream_returns_failed(self):
        engine = ZyeTTSEngine()
        engine._available = True

        async def _bad_stream():
            raise RuntimeError("network gone")
            yield  # make it an async generator

        mock_comm = MagicMock()
        mock_comm.stream = _bad_stream

        with patch("zye_tts.Communicate", return_value=mock_comm):
            result = self._run(engine.synthesize("test"))

        self.assertEqual(result.status, "FAILED")
        self.assertIn("network gone", result.error or "")

    def test_34_input_text_not_mutated(self):
        engine = ZyeTTSEngine()
        engine._available = True
        original = "Hello World"
        mock_comm = _make_mock_communicate(FAKE_MP3)
        with patch("zye_tts.Communicate", return_value=mock_comm):
            result = self._run(engine.synthesize(original))
        self.assertEqual(result.text, original)
        self.assertEqual(original, "Hello World")  # unchanged


# ---------------------------------------------------------------------------
# ZyeTTSEngine synthesize_sync Tests
# ---------------------------------------------------------------------------

class TestZyeTTSEngineSynthesizeSync(unittest.TestCase):
    """Tests for the blocking synthesize_sync() wrapper."""

    def test_35_sync_empty_text_returns_empty(self):
        engine = ZyeTTSEngine()
        result = engine.synthesize_sync("")
        self.assertEqual(result.status, "EMPTY")

    def test_36_sync_unavailable_returns_unavailable(self):
        engine = ZyeTTSEngine()
        engine._available = False
        result = engine.synthesize_sync("hello")
        self.assertEqual(result.status, "UNAVAILABLE")

    def test_37_sync_success_with_mock(self):
        engine = ZyeTTSEngine()
        engine._available = True
        mock_comm = _make_mock_communicate(FAKE_MP3)
        with patch("zye_tts.Communicate", return_value=mock_comm):
            result = engine.synthesize_sync("hello sync")
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(result.audio_bytes, FAKE_MP3)

    def test_38_sync_error_propagated(self):
        engine = ZyeTTSEngine()
        engine._available = True

        async def _bad_stream():
            raise ValueError("bad voice")
            yield

        mock_comm = MagicMock()
        mock_comm.stream = _bad_stream
        with patch("zye_tts.Communicate", return_value=mock_comm):
            result = engine.synthesize_sync("test")
        self.assertIn(result.status, ("FAILED",))


# ---------------------------------------------------------------------------
# ZyeTTSEngine say() Tests
# ---------------------------------------------------------------------------

class TestZyeTTSEngineSay(unittest.TestCase):
    """Tests for say() with playback suppressed."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_39_say_empty_text_returns_empty(self):
        engine = ZyeTTSEngine(TTSConfig(playback_enabled=False))
        result = self._run(engine.say(""))
        self.assertEqual(result.status, "EMPTY")

    def test_40_say_success_calls_play(self):
        engine = ZyeTTSEngine(TTSConfig(playback_enabled=True))
        engine._available = True
        mock_comm = _make_mock_communicate(FAKE_MP3)
        with patch("zye_tts.Communicate", return_value=mock_comm):
            with patch.object(engine, "_play_mp3_bytes") as mock_play:
                result = self._run(engine.say("play this"))
        self.assertEqual(result.status, "SUCCESS")
        mock_play.assert_called_once_with(FAKE_MP3)

    def test_41_say_playback_disabled_no_play(self):
        engine = ZyeTTSEngine(TTSConfig(playback_enabled=False))
        engine._available = True
        mock_comm = _make_mock_communicate(FAKE_MP3)
        with patch("zye_tts.Communicate", return_value=mock_comm):
            with patch.object(engine, "_play_mp3_bytes") as mock_play:
                result = self._run(engine.say("no play"))
        mock_play.assert_not_called()


# ---------------------------------------------------------------------------
# Module-level convenience Tests
# ---------------------------------------------------------------------------

class TestModuleConvenience(unittest.TestCase):
    """Tests for get_default_engine() and speak()."""

    def test_42_get_default_engine_returns_instance(self):
        engine = get_default_engine()
        self.assertIsInstance(engine, ZyeTTSEngine)

    def test_43_get_default_engine_singleton(self):
        e1 = get_default_engine()
        e2 = get_default_engine()
        self.assertIs(e1, e2)

    def test_44_speak_returns_tts_result(self):
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(speak(""))
        finally:
            loop.close()
        self.assertIsInstance(result, TTSResult)


# ---------------------------------------------------------------------------
# Exception hierarchy Tests
# ---------------------------------------------------------------------------

class TestTTSExceptions(unittest.TestCase):
    """Tests for the exception class hierarchy."""

    def test_45_ttserror_is_base_exception(self):
        self.assertTrue(issubclass(TTSError, Exception))

    def test_46_unavailable_is_ttserror(self):
        self.assertTrue(issubclass(TTSUnavailableError, TTSError))

    def test_47_synthesis_error_is_ttserror(self):
        self.assertTrue(issubclass(TTSSynthesisError, TTSError))

    def test_48_playback_error_is_ttserror(self):
        self.assertTrue(issubclass(TTSPlaybackError, TTSError))

    def test_49_config_error_is_ttserror(self):
        self.assertTrue(issubclass(TTSConfigError, TTSError))

    def test_50_can_raise_and_catch(self):
        with self.assertRaises(TTSError):
            raise TTSSynthesisError("test error")


# ---------------------------------------------------------------------------
# zye_voice.edge_tts_engine Tests (Day 10 v4.0 Specification)
# ---------------------------------------------------------------------------

from zye_voice.edge_tts_engine import (
    EdgeTTSConfig,
    ZyeEdgeTTSEngine,
    split_into_sentences,
)
from zye_voice.playback import ZyeAudioPlayback, PlaybackConfig


class TestZyeEdgeTTSEngineModular(unittest.TestCase):
    """Test suite for the modular ZyeEdgeTTSEngine in zye_voice package."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_51_split_into_sentences_empty(self):
        self.assertEqual(split_into_sentences(""), [])
        self.assertEqual(split_into_sentences("   "), [])

    def test_52_split_into_sentences_short(self):
        chunks = split_into_sentences("Hello world. How are you?")
        self.assertEqual(chunks, ["Hello world. How are you?"])

    def test_53_split_into_sentences_preserves_order(self):
        text = "First sentence! Second sentence? Third sentence."
        chunks = split_into_sentences(text, max_chars=30)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], "First sentence!")
        self.assertEqual(chunks[1], "Second sentence?")
        self.assertEqual(chunks[2], "Third sentence.")

    def test_54_split_into_sentences_long_single_sentence(self):
        text = "word " * 100
        chunks = split_into_sentences(text, max_chars=50)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertLessEqual(len(c), 55)

    def test_55_edge_engine_init_defaults(self):
        engine = ZyeEdgeTTSEngine()
        self.assertTrue(engine.config.enabled)
        self.assertEqual(engine.config.voice, "en-IN-NeerjaNeural")
        self.assertEqual(engine.config.provider, "edge_tts")

    def test_56_edge_engine_default_voice_neerja(self):
        cfg = EdgeTTSConfig()
        self.assertEqual(cfg.voice, "en-IN-NeerjaNeural")

    def test_57_edge_engine_empty_text_returns_none(self):
        engine = ZyeEdgeTTSEngine()
        res = self._run(engine.generate_audio(""))
        self.assertIsNone(res)
        res_ws = self._run(engine.generate_audio("   "))
        self.assertIsNone(res_ws)

    def test_58_edge_engine_generate_audio_mocked(self):
        engine = ZyeEdgeTTSEngine()
        mock_comm = AsyncMock()
        mock_comm.save = AsyncMock(return_value=None)

        with patch("zye_voice.edge_tts_engine.edge_tts.Communicate", return_value=mock_comm):
            path = self._run(engine.generate_audio("Hello Zye"))
            self.assertIsNotNone(path)
            self.assertTrue(Path(path).is_file())
            # Clean up
            ZyeEdgeTTSEngine._safe_remove_file(path)

    def test_59_edge_engine_english_text(self):
        engine = ZyeEdgeTTSEngine()
        mock_comm = AsyncMock()
        with patch("zye_voice.edge_tts_engine.edge_tts.Communicate", return_value=mock_comm):
            path = self._run(engine.generate_audio("System diagnostic complete."))
            self.assertIsNotNone(path)
            ZyeEdgeTTSEngine._safe_remove_file(path)

    def test_60_edge_engine_tamil_text(self):
        engine = ZyeEdgeTTSEngine()
        mock_comm = AsyncMock()
        with patch("zye_voice.edge_tts_engine.edge_tts.Communicate", return_value=mock_comm):
            path = self._run(engine.generate_audio("வணக்கம், நான் உங்கள் AI உதவியாளர்."))
            self.assertIsNotNone(path)
            ZyeEdgeTTSEngine._safe_remove_file(path)

    def test_61_edge_engine_tanglish_text(self):
        engine = ZyeEdgeTTSEngine()
        mock_comm = AsyncMock()
        with patch("zye_voice.edge_tts_engine.edge_tts.Communicate", return_value=mock_comm):
            path = self._run(engine.generate_audio("Konjam clear-ah kekkala, thirumba solreengala?"))
            self.assertIsNotNone(path)
            ZyeEdgeTTSEngine._safe_remove_file(path)

    def test_62_edge_engine_temp_file_cleaned_after_speak(self):
        created_paths = []
        real_generate = ZyeEdgeTTSEngine.generate_audio

        mock_pb = MagicMock(spec=ZyeAudioPlayback)
        mock_pb.play_mp3 = AsyncMock(return_value=True)
        engine = ZyeEdgeTTSEngine(playback=mock_pb)

        mock_comm = AsyncMock()
        with patch("zye_voice.edge_tts_engine.edge_tts.Communicate", return_value=mock_comm):
            async def _test():
                res = await engine.speak("Testing temporary file cleanup.")
                self.assertTrue(res)

            self._run(_test())
            # Ensure no orphaned mp3 files remain
            mock_pb.play_mp3.assert_called_once()
            called_path = mock_pb.play_mp3.call_args[0][0]
            self.assertFalse(Path(called_path).is_file(), "Temp MP3 was not deleted!")

    def test_63_edge_engine_speak_chunks(self):
        mock_pb = MagicMock(spec=ZyeAudioPlayback)
        mock_pb.play_mp3 = AsyncMock(return_value=True)
        engine = ZyeEdgeTTSEngine(playback=mock_pb)

        mock_comm = AsyncMock()
        with patch("zye_voice.edge_tts_engine.edge_tts.Communicate", return_value=mock_comm):
            long_text = "Sentence one. " * 40
            res = self._run(engine.speak_chunks(long_text))
            self.assertTrue(res)
            self.assertGreater(mock_pb.play_mp3.call_count, 1)

    def test_64_edge_engine_cloud_tts_disabled_fallback(self):
        cfg = EdgeTTSConfig(allow_cloud_tts=False)
        engine = ZyeEdgeTTSEngine(config=cfg)
        res = self._run(engine.speak("Privacy mode text"))
        self.assertTrue(res)  # Falls back to console print gracefully

    def test_65_edge_engine_timeout_handled(self):
        cfg = EdgeTTSConfig(timeout_seconds=0.001, max_retries=0)
        engine = ZyeEdgeTTSEngine(config=cfg)

        async def _slow_save(path):
            await asyncio.sleep(5)

        mock_comm = MagicMock()
        mock_comm.save = _slow_save

        with patch("zye_voice.edge_tts_engine.edge_tts.Communicate", return_value=mock_comm):
            path = self._run(engine.generate_audio("Test timeout"))
            self.assertIsNone(path)

    def test_66_edge_engine_retry_on_network_failure(self):
        cfg = EdgeTTSConfig(max_retries=1, retry_delay_seconds=0.01)
        engine = ZyeEdgeTTSEngine(config=cfg)

        mock_comm = AsyncMock()
        # Fail once, then succeed
        mock_comm.save = AsyncMock(side_effect=[ConnectionError("DNS drop"), None])

        with patch("zye_voice.edge_tts_engine.edge_tts.Communicate", return_value=mock_comm):
            path = self._run(engine.generate_audio("Test retry"))
            self.assertIsNotNone(path)
            ZyeEdgeTTSEngine._safe_remove_file(path)

    def test_67_edge_engine_get_status(self):
        engine = ZyeEdgeTTSEngine()
        status = engine.get_status()
        self.assertIn("enabled", status)
        self.assertIn("voice", status)
        self.assertIn("provider", status)
        self.assertIn("playback", status)

    def test_68_edge_engine_safe_remove_file(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        self.assertTrue(Path(tmp.name).is_file())
        ZyeEdgeTTSEngine._safe_remove_file(tmp.name)
        self.assertFalse(Path(tmp.name).is_file())

    def test_69_edge_engine_stop_and_close(self):
        mock_pb = MagicMock(spec=ZyeAudioPlayback)
        mock_pb.stop = AsyncMock()
        mock_pb.close = AsyncMock()
        engine = ZyeEdgeTTSEngine(playback=mock_pb)
        self._run(engine.stop())
        mock_pb.stop.assert_called_once()
        self._run(engine.close())
        mock_pb.close.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
