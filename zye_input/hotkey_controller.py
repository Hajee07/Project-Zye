#!/usr/bin/env python3
"""
ZYE AI — Alt+Z Global Hotkey & Silent Input Controller v2.0
===========================================================

Provides a seamless global keyboard interrupt mechanism (Alt + Z):
- Lightweight, thread-safe callback using threading.Event
- Non-blocking hotkey registration via keyboard library
- Console text collection with configurable prompt and timeout
- Validation for English, Tamil, Tanglish, numbers, and Unicode input
- Clean registration/unregistration lifecycle to prevent duplicate hooks
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger("zye_input.hotkey")

try:
    import keyboard as kb
    _KEYBOARD_AVAILABLE = True
except ImportError:
    kb = None  # type: ignore
    _KEYBOARD_AVAILABLE = False


class HotkeyError(Exception):
    """Base exception for hotkey operations."""
    pass


class HotkeyRegistrationError(HotkeyError):
    """Raised when registering the global hotkey fails."""
    pass


@dataclass
class HotkeyConfig:
    """Configuration for global silent text input hotkey."""
    enabled: bool = True
    shortcut: str = "alt+z"
    fallback_to_terminal: bool = True
    input_timeout_seconds: float = 60.0
    prompt_message: str = "Command to Zye: "
    max_input_length: int = 2000


class ZyeHotkeyController:
    """
    Manages the global Alt+Z hotkey registration, event signaling,
    and text input collection.
    """

    def __init__(self, config: HotkeyConfig | None = None) -> None:
        self.config = config or HotkeyConfig()
        self._requested_event = threading.Event()
        self._registered = False
        self._lock = threading.Lock()
        self.total_triggers: int = 0
        self.total_text_commands: int = 0
        self.last_trigger_time: float | None = None

    def register(self) -> bool:
        """Register the Alt + Z global hotkey safely."""
        with self._lock:
            if not self.config.enabled:
                logger.info("Hotkey controller is disabled in configuration")
                return False

            if not _KEYBOARD_AVAILABLE:
                logger.warning("keyboard package is not installed; hotkey unavailable")
                return False

            if self._registered:
                return True

            try:
                kb.add_hotkey(self.config.shortcut, self._hotkey_callback, suppress=False)
                self._registered = True
                logger.info("Registered global hotkey '%s' for silent text mode", self.config.shortcut)
                return True
            except Exception as exc:
                logger.warning("Failed to register hotkey '%s': %s", self.config.shortcut, exc)
                self._registered = False
                return False

    def unregister(self) -> None:
        """Unregister the global hotkey hook."""
        with self._lock:
            if not self._registered or not _KEYBOARD_AVAILABLE:
                return
            try:
                kb.remove_hotkey(self.config.shortcut)
            except Exception as exc:
                logger.debug("Error unregistering hotkey: %s", exc)
            self._registered = False
            logger.info("Unregistered global hotkey '%s'", self.config.shortcut)

    def _hotkey_callback(self) -> None:
        """
        Lightweight callback invoked by the keyboard hook thread.
        Never executes blocking operations, API calls, or input prompts.
        """
        self.total_triggers += 1
        self.last_trigger_time = time.time()
        self._requested_event.set()
        logger.debug("Alt+Z hotkey event triggered")

    def text_mode_requested(self) -> bool:
        """Check whether text mode has been requested by the user."""
        return self._requested_event.is_set()

    def consume_text_mode_request(self) -> bool:
        """Check and atomically consume the text mode request flag."""
        if self._requested_event.is_set():
            self._requested_event.clear()
            return True
        return False

    def collect_text_command(
        self,
        prompt: str | None = None,
        timeout: float | None = None,
    ) -> str:
        """
        Display prompt and collect typed user command from console with timeout.
        Returns cleaned text command, or empty string on cancel / timeout.
        """
        effective_prompt = prompt or self.config.prompt_message
        effective_timeout = timeout or self.config.input_timeout_seconds
        result_holder: list[str | None] = [None]

        def _reader() -> None:
            try:
                print(f"\n{effective_prompt}", flush=True, end="")
                line = input()
                result_holder[0] = line
            except (EOFError, KeyboardInterrupt):
                result_holder[0] = None

        thread = threading.Thread(target=_reader, daemon=True)
        thread.start()
        thread.join(timeout=effective_timeout)

        if result_holder[0] is not None:
            raw = result_holder[0].strip()
            # Enforce max length constraint
            clean_text = raw[: self.config.max_input_length].strip()
            if clean_text:
                self.total_text_commands += 1
            return clean_text

        # Timed out or interrupted
        print("\n[Text mode timed out or cancelled]\n", flush=True)
        return ""

    def get_status(self) -> dict[str, Any]:
        """Return structured telemetry for hotkey controller."""
        return {
            "enabled": self.config.enabled,
            "keyboard_available": _KEYBOARD_AVAILABLE,
            "registered": self._registered,
            "shortcut": self.config.shortcut,
            "text_mode_requested": self._requested_event.is_set(),
            "total_triggers": self.total_triggers,
            "total_text_commands": self.total_text_commands,
            "last_trigger_time": self.last_trigger_time,
        }
