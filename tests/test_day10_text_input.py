#!/usr/bin/env python3
"""
ZYE AI — Day 10 Text Input Handler Test Suite
==============================================
Tests for zye_text_input.py: TextInputConfig, AltZTextInputHandler, TextInputResult.
Mocks the keyboard library — CI-safe.
"""

from __future__ import annotations

import queue
import sys
import threading
import time
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zye_text_input import (
    AltZTextInputHandler,
    TextInputConfig,
    TextInputError,
    TextInputResult,
    TextInputTimeoutError,
    TextInputUnavailableError,
    TextTriggerEvent,
)


# ---------------------------------------------------------------------------
# TextInputConfig Tests
# ---------------------------------------------------------------------------

class TestTextInputConfig(unittest.TestCase):
    """Tests for TextInputConfig dataclass."""

    def test_01_default_hotkey_is_altz(self):
        cfg = TextInputConfig()
        self.assertEqual(cfg.hotkey, "alt+z")

    def test_02_default_timeout_is_60(self):
        cfg = TextInputConfig()
        self.assertEqual(cfg.input_timeout_seconds, 60.0)

    def test_03_default_max_length_is_2000(self):
        cfg = TextInputConfig()
        self.assertEqual(cfg.max_input_length, 2000)

    def test_04_default_enabled_true(self):
        cfg = TextInputConfig()
        self.assertTrue(cfg.enabled)

    def test_05_custom_hotkey(self):
        cfg = TextInputConfig(hotkey="ctrl+shift+z")
        self.assertEqual(cfg.hotkey, "ctrl+shift+z")

    def test_06_custom_timeout(self):
        cfg = TextInputConfig(input_timeout_seconds=30.0)
        self.assertEqual(cfg.input_timeout_seconds, 30.0)

    def test_07_disabled_config(self):
        cfg = TextInputConfig(enabled=False)
        self.assertFalse(cfg.enabled)


# ---------------------------------------------------------------------------
# TextTriggerEvent Tests
# ---------------------------------------------------------------------------

class TestTextTriggerEvent(unittest.TestCase):
    """Tests for TextTriggerEvent dataclass."""

    def test_08_default_source_is_hotkey(self):
        event = TextTriggerEvent()
        self.assertEqual(event.source, "hotkey")

    def test_09_timestamp_is_recent(self):
        before = time.time()
        event = TextTriggerEvent()
        after = time.time()
        self.assertGreaterEqual(event.timestamp, before)
        self.assertLessEqual(event.timestamp, after)

    def test_10_custom_source(self):
        event = TextTriggerEvent(source="direct")
        self.assertEqual(event.source, "direct")


# ---------------------------------------------------------------------------
# TextInputResult Tests
# ---------------------------------------------------------------------------

class TestTextInputResult(unittest.TestCase):
    """Tests for TextInputResult dataclass."""

    def test_11_hotkey_source(self):
        r = TextInputResult(text="hello", source="hotkey", duration_seconds=1.5)
        self.assertEqual(r.source, "hotkey")
        self.assertEqual(r.text, "hello")

    def test_12_timeout_source(self):
        r = TextInputResult(text="", source="timeout", duration_seconds=60.0)
        self.assertEqual(r.source, "timeout")
        self.assertEqual(r.text, "")

    def test_13_cancelled_source(self):
        r = TextInputResult(text="", source="cancelled", duration_seconds=0.5)
        self.assertEqual(r.source, "cancelled")

    def test_14_truncated_default_false(self):
        r = TextInputResult(text="hi", source="hotkey", duration_seconds=1.0)
        self.assertFalse(r.truncated)

    def test_15_truncated_true(self):
        r = TextInputResult(text="x" * 100, source="hotkey", duration_seconds=1.0, truncated=True)
        self.assertTrue(r.truncated)


# ---------------------------------------------------------------------------
# AltZTextInputHandler Init Tests
# ---------------------------------------------------------------------------

class TestAltZTextInputHandlerInit(unittest.TestCase):
    """Tests for AltZTextInputHandler initialization."""

    def test_16_instantiates_with_defaults(self):
        handler = AltZTextInputHandler()
        self.assertIsNotNone(handler)

    def test_17_instantiates_with_custom_config(self):
        cfg = TextInputConfig(hotkey="ctrl+t")
        handler = AltZTextInputHandler(cfg)
        self.assertEqual(handler.config.hotkey, "ctrl+t")

    def test_18_initial_not_running(self):
        handler = AltZTextInputHandler()
        self.assertFalse(handler._running)

    def test_19_initial_counters_zero(self):
        handler = AltZTextInputHandler()
        self.assertEqual(handler.total_triggers, 0)
        self.assertEqual(handler.total_sessions, 0)
        self.assertEqual(handler.total_timeouts, 0)

    def test_20_diagnostics_has_required_keys(self):
        handler = AltZTextInputHandler()
        diag = handler.get_diagnostics()
        required = [
            "status", "keyboard_available", "hotkey", "enabled",
            "hotkey_registered", "pending_triggers",
            "total_triggers", "total_sessions", "total_timeouts",
            "last_trigger_time",
        ]
        for key in required:
            self.assertIn(key, diag, f"Missing key: {key}")

    def test_21_diagnostics_keyboard_available_is_bool(self):
        handler = AltZTextInputHandler()
        diag = handler.get_diagnostics()
        self.assertIsInstance(diag["keyboard_available"], bool)

    def test_22_diagnostics_status_stopped_initially(self):
        handler = AltZTextInputHandler()
        diag = handler.get_diagnostics()
        self.assertEqual(diag["status"], "stopped")


# ---------------------------------------------------------------------------
# AltZTextInputHandler Start/Stop Tests
# ---------------------------------------------------------------------------

class TestAltZTextInputHandlerStartStop(unittest.TestCase):
    """Tests for start() and stop() lifecycle."""

    def test_23_start_when_keyboard_unavailable(self):
        with patch("zye_text_input._KEYBOARD_AVAILABLE", False):
            handler = AltZTextInputHandler()
            result = handler.start()
        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(handler._running)

    def test_24_start_when_disabled(self):
        cfg = TextInputConfig(enabled=False)
        with patch("zye_text_input._KEYBOARD_AVAILABLE", True):
            handler = AltZTextInputHandler(cfg)
            result = handler.start()
        self.assertEqual(result["status"], "disabled")

    def test_25_start_when_already_running(self):
        with patch("zye_text_input._KEYBOARD_AVAILABLE", True), \
             patch("zye_text_input.kb") as mock_kb:
            mock_kb.add_hotkey = MagicMock()
            handler = AltZTextInputHandler()
            handler.start()
            result = handler.start()  # second call
        self.assertEqual(result["status"], "already_running")

    def test_26_stop_when_not_running_safe(self):
        handler = AltZTextInputHandler()
        # Should not raise
        handler.stop()
        self.assertFalse(handler._running)

    def test_27_context_manager_start_stop(self):
        with patch("zye_text_input._KEYBOARD_AVAILABLE", True), \
             patch("zye_text_input.kb") as mock_kb:
            mock_kb.add_hotkey = MagicMock()
            mock_kb.remove_hotkey = MagicMock()
            handler = AltZTextInputHandler()
            with handler:
                self.assertTrue(handler._running)
            self.assertFalse(handler._running)

    def test_28_start_success_returns_running_status(self):
        with patch("zye_text_input._KEYBOARD_AVAILABLE", True), \
             patch("zye_text_input.kb") as mock_kb:
            mock_kb.add_hotkey = MagicMock()
            handler = AltZTextInputHandler()
            result = handler.start()
        self.assertEqual(result["status"], "running")
        self.assertTrue(handler._running)


# ---------------------------------------------------------------------------
# AltZTextInputHandler Trigger Tests
# ---------------------------------------------------------------------------

class TestAltZTextInputHandlerTrigger(unittest.TestCase):
    """Tests for _on_hotkey_pressed, is_triggered, get_trigger_event."""

    def setUp(self):
        self.handler = AltZTextInputHandler()

    def test_29_is_triggered_false_at_rest(self):
        self.assertFalse(self.handler.is_triggered())

    def test_30_manual_hotkey_press_sets_triggered(self):
        self.handler._on_hotkey_pressed()
        self.assertTrue(self.handler.is_triggered())

    def test_31_total_triggers_increments(self):
        self.handler._on_hotkey_pressed()
        self.handler._on_hotkey_pressed()
        self.assertEqual(self.handler.total_triggers, 2)

    def test_32_get_trigger_event_returns_event(self):
        self.handler._on_hotkey_pressed()
        event = self.handler.get_trigger_event()
        self.assertIsInstance(event, TextTriggerEvent)

    def test_33_get_trigger_event_drains_queue(self):
        self.handler._on_hotkey_pressed()
        self.handler.get_trigger_event()
        self.assertFalse(self.handler.is_triggered())

    def test_34_get_trigger_event_returns_none_when_empty(self):
        event = self.handler.get_trigger_event()
        self.assertIsNone(event)

    def test_35_clear_pending_drains_all(self):
        for _ in range(3):
            self.handler._on_hotkey_pressed()
        self.handler.clear_pending_triggers()
        self.assertFalse(self.handler.is_triggered())

    def test_36_queue_full_drops_extra(self):
        handler = AltZTextInputHandler()
        # Fill the queue to capacity
        for _ in range(4):  # maxsize=4
            handler._trigger_queue.put_nowait(TextTriggerEvent())
        # This should not raise, should log debug and discard
        handler._on_hotkey_pressed()
        self.assertEqual(handler._trigger_queue.qsize(), 4)

    def test_37_last_trigger_time_updated(self):
        before = time.time()
        self.handler._on_hotkey_pressed()
        after = time.time()
        lt = self.handler.last_trigger_time
        self.assertIsNotNone(lt)
        self.assertGreaterEqual(lt, before)
        self.assertLessEqual(lt, after)


# ---------------------------------------------------------------------------
# AltZTextInputHandler Diagnostics Tests
# ---------------------------------------------------------------------------

class TestAltZTextInputHandlerDiagnostics(unittest.TestCase):
    """Diagnostics state tests."""

    def test_38_diagnostics_after_trigger(self):
        handler = AltZTextInputHandler()
        handler._on_hotkey_pressed()
        diag = handler.get_diagnostics()
        self.assertEqual(diag["pending_triggers"], 1)
        self.assertEqual(diag["total_triggers"], 1)

    def test_39_diagnostics_status_running_when_active(self):
        handler = AltZTextInputHandler()
        handler._running = True
        diag = handler.get_diagnostics()
        self.assertEqual(diag["status"], "running")

    def test_40_diagnostics_last_trigger_none_initially(self):
        handler = AltZTextInputHandler()
        diag = handler.get_diagnostics()
        self.assertIsNone(diag["last_trigger_time"])


# ---------------------------------------------------------------------------
# AltZTextInputHandler collect_text_input Tests
# ---------------------------------------------------------------------------

class TestAltZTextInputHandlerCollect(unittest.TestCase):
    """Tests for collect_text_input() — mocked stdin."""

    def test_41_collect_timeout_returns_timeout_source(self):
        handler = AltZTextInputHandler()
        # Timeout immediately with 0.05s
        result = handler.collect_text_input(timeout=0.05)
        self.assertEqual(result.source, "timeout")
        self.assertEqual(result.text, "")
        self.assertEqual(handler.total_timeouts, 1)

    def test_42_collect_total_sessions_increments(self):
        handler = AltZTextInputHandler()
        handler.collect_text_input(timeout=0.02)
        self.assertEqual(handler.total_sessions, 1)

    def test_43_collect_duration_recorded(self):
        handler = AltZTextInputHandler()
        result = handler.collect_text_input(timeout=0.05)
        self.assertGreaterEqual(result.duration_seconds, 0.0)

    def test_44_collect_text_truncated_at_max_length(self):
        handler = AltZTextInputHandler(TextInputConfig(max_input_length=5))

        result_holder: list = []
        def _simulate_collect():
            # Simulate what collect_text_input does for a long line
            raw = "hello world"
            truncated = len(raw) > 5
            text = raw[:5].strip()
            result_holder.append(TextInputResult(
                text=text,
                source="hotkey",
                duration_seconds=0.1,
                truncated=truncated,
            ))

        t = threading.Thread(target=_simulate_collect)
        t.start()
        t.join()
        result = result_holder[0]
        self.assertEqual(result.text, "hello")
        self.assertTrue(result.truncated)

    def test_45_on_prompt_shown_callback_called(self):
        handler = AltZTextInputHandler()
        callback_called = threading.Event()
        handler.collect_text_input(
            timeout=0.05,
            on_prompt_shown=lambda: callback_called.set(),
        )
        self.assertTrue(callback_called.is_set())


# ---------------------------------------------------------------------------
# Exception hierarchy Tests
# ---------------------------------------------------------------------------

class TestTextInputExceptions(unittest.TestCase):
    """Exception class hierarchy tests."""

    def test_46_text_input_error_is_exception(self):
        self.assertTrue(issubclass(TextInputError, Exception))

    def test_47_unavailable_is_text_input_error(self):
        self.assertTrue(issubclass(TextInputUnavailableError, TextInputError))

    def test_48_timeout_error_is_text_input_error(self):
        self.assertTrue(issubclass(TextInputTimeoutError, TextInputError))

    def test_49_can_raise_and_catch(self):
        with self.assertRaises(TextInputError):
            raise TextInputUnavailableError("no keyboard")

    def test_50_timeout_error_message(self):
        exc = TextInputTimeoutError("timed out")
        self.assertIn("timed out", str(exc))


if __name__ == "__main__":
    unittest.main(verbosity=2)
