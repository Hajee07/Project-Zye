#!/usr/bin/env python3
"""
ZYE AI — Day 10 Hotkey Controller Test Suite
============================================
Tests for zye_input.hotkey_controller: ZyeHotkeyController, HotkeyConfig.
All OS keyboard hook calls are mocked — CI-safe.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zye_input.hotkey_controller import HotkeyConfig, ZyeHotkeyController


class TestZyeHotkeyController(unittest.TestCase):
    """Test suite for global Alt+Z hotkey controller."""

    def test_01_init_defaults(self):
        ctrl = ZyeHotkeyController()
        self.assertTrue(ctrl.config.enabled)
        self.assertEqual(ctrl.config.shortcut, "alt+z")
        self.assertFalse(ctrl.text_mode_requested())

    def test_02_register_success(self):
        with patch("zye_input.hotkey_controller._KEYBOARD_AVAILABLE", True), \
             patch("zye_input.hotkey_controller.kb") as mock_kb:
            ctrl = ZyeHotkeyController()
            res = ctrl.register()
            self.assertTrue(res)
            mock_kb.add_hotkey.assert_called_once()
            self.assertTrue(ctrl._registered)

    def test_03_duplicate_registration_prevention(self):
        with patch("zye_input.hotkey_controller._KEYBOARD_AVAILABLE", True), \
             patch("zye_input.hotkey_controller.kb") as mock_kb:
            ctrl = ZyeHotkeyController()
            self.assertTrue(ctrl.register())
            # Second call should be a no-op
            self.assertTrue(ctrl.register())
            self.assertEqual(mock_kb.add_hotkey.call_count, 1)

    def test_04_register_when_disabled(self):
        ctrl = ZyeHotkeyController(HotkeyConfig(enabled=False))
        self.assertFalse(ctrl.register())

    def test_05_register_when_keyboard_missing(self):
        with patch("zye_input.hotkey_controller._KEYBOARD_AVAILABLE", False):
            ctrl = ZyeHotkeyController()
            self.assertFalse(ctrl.register())

    def test_06_os_permission_failure_handled(self):
        with patch("zye_input.hotkey_controller._KEYBOARD_AVAILABLE", True), \
             patch("zye_input.hotkey_controller.kb") as mock_kb:
            mock_kb.add_hotkey.side_effect = PermissionError("Root required")
            ctrl = ZyeHotkeyController()
            self.assertFalse(ctrl.register())

    def test_07_callback_sets_event_and_increments_counter(self):
        ctrl = ZyeHotkeyController()
        self.assertFalse(ctrl.text_mode_requested())
        ctrl._hotkey_callback()
        self.assertTrue(ctrl.text_mode_requested())
        self.assertEqual(ctrl.total_triggers, 1)
        self.assertIsNotNone(ctrl.last_trigger_time)

    def test_08_consume_text_mode_request(self):
        ctrl = ZyeHotkeyController()
        ctrl._hotkey_callback()
        self.assertTrue(ctrl.text_mode_requested())
        consumed = ctrl.consume_text_mode_request()
        self.assertTrue(consumed)
        # Second consume should return False
        self.assertFalse(ctrl.consume_text_mode_request())
        self.assertFalse(ctrl.text_mode_requested())

    def test_09_unregister_removes_hotkey(self):
        with patch("zye_input.hotkey_controller._KEYBOARD_AVAILABLE", True), \
             patch("zye_input.hotkey_controller.kb") as mock_kb:
            ctrl = ZyeHotkeyController()
            ctrl.register()
            ctrl.unregister()
            mock_kb.remove_hotkey.assert_called_once_with("alt+z")
            self.assertFalse(ctrl._registered)

    def test_10_collect_text_command_timeout(self):
        ctrl = ZyeHotkeyController(HotkeyConfig(input_timeout_seconds=0.02))
        cmd = ctrl.collect_text_command()
        self.assertEqual(cmd, "")

    def test_11_get_status_telemetry(self):
        ctrl = ZyeHotkeyController()
        status = ctrl.get_status()
        self.assertIn("enabled", status)
        self.assertIn("keyboard_available", status)
        self.assertIn("registered", status)
        self.assertIn("shortcut", status)
        self.assertIn("text_mode_requested", status)


if __name__ == "__main__":
    unittest.main(verbosity=2)
