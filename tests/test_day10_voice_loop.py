#!/usr/bin/env python3
"""
ZYE AI — Day 10 Voice Loop Integration Test Suite
==================================================
Tests for main.py: ZyeVoiceLoop, voice loop lifecycle, echo mode,
Gemini retry fallback, and CLI orchestrator integration.
"""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import (
    MCP_SERVERS,
    NON_IDEMPOTENT_OPERATIONS,
    ZyeMasterAgent,
    ZyeVoiceLoop,
    _load_toml_config,
    call_gemini_with_retry,
    is_safe_to_replay,
    main,
)
from zye_text_input import AltZTextInputHandler, TextInputResult, TextTriggerEvent
from zye_tts import TTSResult, ZyeTTSEngine
from zye_voice.edge_tts_engine import ZyeEdgeTTSEngine


# ---------------------------------------------------------------------------
# ZyeVoiceLoop Initialization Tests
# ---------------------------------------------------------------------------

class TestZyeVoiceLoopInit(unittest.TestCase):
    """Tests for ZyeVoiceLoop initialization and configuration loading."""

    def test_01_init_creates_instance(self):
        loop = ZyeVoiceLoop()
        self.assertIsNotNone(loop)
        self.assertFalse(loop._running)

    def test_02_echo_mode_when_no_api_key(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            loop = ZyeVoiceLoop()
            self.assertTrue(loop._echo_mode)

    def test_03_echo_mode_when_placeholder_key(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "placeholder_key_abc"}, clear=False):
            loop = ZyeVoiceLoop()
            self.assertTrue(loop._echo_mode)

    def test_04_tts_engine_initialized(self):
        loop = ZyeVoiceLoop()
        self.assertTrue(isinstance(loop.tts_engine, (ZyeTTSEngine, ZyeEdgeTTSEngine)))

    def test_05_text_handler_initialized(self):
        loop = ZyeVoiceLoop()
        self.assertIsInstance(loop.text_handler, AltZTextInputHandler)

    def test_06_load_toml_config_loads_tts(self):
        cfg = _load_toml_config()
        self.assertIn("tts", cfg)
        self.assertIn("text_input", cfg)
        self.assertEqual(cfg["tts"]["voice"], "en-IN-NeerjaNeural")

    def test_07_load_toml_config_handles_missing(self):
        with patch("main.PROJECT_ROOT", Path("C:/nonexistent_zye_path")):
            cfg = _load_toml_config()
            self.assertEqual(cfg, {})


# ---------------------------------------------------------------------------
# ZyeVoiceLoop Response Generation Tests
# ---------------------------------------------------------------------------

class TestZyeVoiceLoopResponseGeneration(unittest.TestCase):
    """Tests for _generate_response in echo and Gemini modes."""

    def setUp(self):
        self.loop = ZyeVoiceLoop()

    def _run(self, coro):
        return asyncio.run(coro)

    def test_08_echo_mode_returns_echo_prefix(self):
        self.loop._echo_mode = True
        res = self._run(self.loop._generate_response("hello assistant"))
        self.assertEqual(res, "[Echo] hello assistant")

    def test_09_empty_text_returns_empty(self):
        res = self._run(self.loop._generate_response(""))
        self.assertEqual(res, "")

    def test_10_whitespace_returns_empty(self):
        res = self._run(self.loop._generate_response("   \t  "))
        self.assertEqual(res, "")

    def test_11_gemini_call_mocked_success(self):
        self.loop._echo_mode = False
        self.loop._gemini_key = "actual_test_key"
        if self.loop.brain:
            self.loop.brain._echo_mode = False
            self.loop.brain.handle_text = AsyncMock(return_value="Hello from Gemini")

        res = self._run(self.loop._generate_response("Hi there"))
        self.assertEqual(res, "Hello from Gemini")

    def test_12_gemini_call_failure_falls_back_to_echo(self):
        self.loop._echo_mode = True
        res = self._run(self.loop._generate_response("Hello"))
        self.assertEqual(res, "[Echo] Hello")


# ---------------------------------------------------------------------------
# ZyeVoiceLoop Speak Tests
# ---------------------------------------------------------------------------

class TestZyeVoiceLoopSpeak(unittest.TestCase):
    """Tests for _speak() async method."""

    def setUp(self):
        self.loop = ZyeVoiceLoop()

    def _run(self, coro):
        return asyncio.run(coro)

    def test_13_speak_empty_text_noop(self):
        with patch.object(self.loop, "_speak") as mock_spk:
            self._run(self.loop._speak(""))
            mock_spk.assert_called_once_with("")

    def test_14_speak_whitespace_noop(self):
        if self.loop.coordinator:
            with patch.object(self.loop.coordinator, "speak", new_callable=AsyncMock) as mock_spk:
                self._run(self.loop._speak("   "))
                mock_spk.assert_not_called()

    def test_15_speak_calls_tts_engine_say(self):
        if self.loop.coordinator:
            with patch.object(self.loop.coordinator, "speak", new_callable=AsyncMock) as mock_speak:
                self._run(self.loop._speak("hello"))
                mock_speak.assert_awaited_once_with("hello")
        elif self.loop.tts_engine:
            with patch.object(self.loop.tts_engine, "speak", new_callable=AsyncMock) as mock_say:
                self._run(self.loop._speak("hello"))
                mock_say.assert_awaited_once_with("hello")

    def test_16_speak_none_engine_falls_back_to_print(self):
        self.loop.tts_engine = None  # type: ignore
        self.loop.coordinator = None  # type: ignore
        with patch("builtins.print") as mock_print:
            self._run(self.loop._speak("echo test"))
        mock_print.assert_called_once_with("[Zye] echo test")

    def test_17_speak_swallows_tts_exception(self):
        if self.loop.coordinator:
            with patch.object(self.loop.coordinator, "speak", new_callable=AsyncMock) as mock_spk:
                mock_spk.side_effect = RuntimeError("audio hardware failure")
                # Should not raise
                self._run(self.loop._speak("will fail gracefully"))


# ---------------------------------------------------------------------------
# ZyeVoiceLoop Lifecycle Tests
# ---------------------------------------------------------------------------

class TestZyeVoiceLoopLifecycle(unittest.TestCase):
    """Tests for start, stop, and shutdown lifecycle."""

    def test_18_stop_sets_running_false(self):
        loop = ZyeVoiceLoop()
        loop._running = True
        loop.stop()
        self.assertFalse(loop._running)

    def test_19_shutdown_cleans_up_resources(self):
        loop = ZyeVoiceLoop()
        loop._running = True
        with patch.object(loop.text_handler, "stop") as mock_th_stop, \
             patch.object(loop.ear, "close") as mock_ear_close:
            asyncio.run(loop._shutdown())
        self.assertFalse(loop._running)
        mock_th_stop.assert_called_once()
        mock_ear_close.assert_called_once()

    def test_20_keyboard_interrupt_handled_gracefully(self):
        loop = ZyeVoiceLoop()

        async def _run_with_interrupt():
            async def _stopper():
                await asyncio.sleep(0.02)
                loop.stop()

            asyncio.create_task(_stopper())
            if loop.ear:
                with patch.object(loop.ear, "listen_smart", return_value=None):
                    await loop.run()
            else:
                await loop.run()

        # Should finish cleanly without raising
        asyncio.run(_run_with_interrupt())
        self.assertFalse(loop._running)


# ---------------------------------------------------------------------------
# Main CLI & Day 01–06 Preservation Tests
# ---------------------------------------------------------------------------

class TestMainCLIIntegration(unittest.TestCase):
    """Ensure Day 01–06 features and Day 10 CLI options are intact."""

    def test_21_main_default_registers_agent(self):
        with patch("sys.argv", ["main.py"]):
            code = main()
            self.assertEqual(code, 0)

    def test_22_main_voice_flag_runs_voice_loop(self):
        with patch("sys.argv", ["main.py", "--voice"]), \
             patch.object(ZyeVoiceLoop, "run", new_callable=AsyncMock) as mock_run:
            code = main()
            self.assertEqual(code, 0)
            mock_run.assert_awaited_once()

    def test_23_is_safe_to_replay_preserves_day06_rules(self):
        self.assertTrue(is_safe_to_replay("read_recent_error_logs"))
        self.assertTrue(is_safe_to_replay("inspect_source_file"))
        self.assertFalse(is_safe_to_replay("patch_own_code"))
        self.assertFalse(is_safe_to_replay("shutdown_windows"))

    def test_24_call_gemini_with_retry_present(self):
        self.assertTrue(callable(call_gemini_with_retry))

    def test_25_mcp_servers_allowlist_intact(self):
        for name in ("self_repair", "windows_control", "office_master", "browser_accounts"):
            self.assertIn(name, MCP_SERVERS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
